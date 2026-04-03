# NBA Analytics Pipeline

Pipeline de Engenharia de Dados de ponta a ponta: extração automatizada de dados da NBA via web scraping, transformação com dbt e armazenamento em PostgreSQL.

---

## Visão Geral

Este projeto implementa um pipeline ETL completo para análise de dados da NBA, utilizando dados públicos do [Basketball Reference](https://www.basketball-reference.com). O objetivo é demonstrar domínio das etapas centrais de Engenharia de Dados — extração, transformação e carga — com ferramentas utilizadas no mercado.

```
Basketball Reference
       │
       │  Selenium + BeautifulSoup (extração)
       ▼
   CSV Seeds
       │
       │  dbt seed (carga no banco)
       ▼
  PostgreSQL (raw)
       │
       │  dbt run (transformação SQL)
       ▼
  PostgreSQL (staging)
       │
       │  (em desenvolvimento)
       ▼
  Camada Enriched (dimensões e fatos)
```

---

## Stack Técnica

| Camada | Tecnologia | Versão | Papel no pipeline |
|---|---|---|---|
| Extração | Python + Selenium | 4.31 | Renderiza páginas com JavaScript e captura HTML |
| Parsing | BeautifulSoup + lxml | 4.13 / 5.4 | Descomenta e navega o DOM do Basketball Reference |
| Transformação | dbt Core | 1.9.10 | Modela e documenta as transformações SQL |
| Armazenamento | PostgreSQL | 17.2 | Data warehouse local via Docker |
| Processamento | pandas | 2.2.3 | Limpeza e exportação dos dados no scraper |
| Ambiente | Python venv | 3.12 | Isolamento de dependências |

### Por que essa stack?

**Selenium em vez de `requests`:** O Basketball Reference renderiza tabelas via JavaScript e insere dados relevantes em blocos HTML comentados. Requisições HTTP simples retornam uma página incompleta. O Selenium com Chromium headless renderiza o JavaScript completo, permitindo capturar o DOM exato que o usuário veria no browser.

**dbt em vez de SQL avulso:** O dbt trata transformações SQL como software — com versionamento, testes, documentação e linhagem de dados. Cada modelo é rastreável, testável e reproduzível. É a ferramenta-padrão do mercado para a camada de transformação em pipelines modernos.

**PostgreSQL em vez de DuckDB ou SQLite:** PostgreSQL oferece tipos de dados ricos (`numeric(p,s)`, `date`), suporte a schemas para separação lógica de camadas (`analytics_raw`), e é a escolha mais comum em ambientes de produção. Docker torna o setup reproduzível em qualquer máquina.

---

## Estrutura do Projeto

```
NBA Analytics Pipeline/
│
├── scraping/                    # Extração de dados
│   ├── players/
│   │   └── players.ipynb        # Roster: nome, posição, time, idade
│   ├── stats/
│   │   └── stats.ipynb          # Médias por jogo da temporada 2024-25
│   ├── teams/
│   │   └── teams_scrap.ipynb    # Histórico de franquias NBA
│   └── contracts/
│       └── nba_contracts.ipynb  # Contratos e salários dos jogadores
│
├── basket_dbt/
│   └── seeds/                   # CSVs gerados pelo scraping
│       ├── players.csv
│       ├── players_stats.csv
│       └── team.csv
│
├── models/
│   └── staging/                 # Camada de transformação
│       ├── stg_players.sql
│       ├── stg_players_stats.sql
│       ├── stg_team.sql
│       └── _src__raw.yml        # Documentação das fontes
│
├── .dbt/
│   └── profiles.yml             # Conexão com PostgreSQL
├── dbt_project.yml              # Configuração do projeto dbt
├── fix_csv.py                   # Utilitário de reparo de CSVs
└── requirements.txt             # Dependências Python
```

---

## Pipeline de Dados em Detalhe

### Etapa 1 — Extração (Scraping)

Os scrapers utilizam um padrão consistente baseado em três funções:

#### `get_rendered_html(url, wait_seconds)`

```python
driver = webdriver.Chrome(service=Service(CHROMEDRIVER_PATH), options=opts)
driver.get(url)
time.sleep(wait_seconds)   # aguarda o JavaScript renderizar
html = driver.page_source
```

Inicia o Chromium em modo headless (sem interface gráfica), navega até a URL e aguarda o JavaScript renderizar a página antes de capturar o HTML completo. O `time.sleep` é necessário porque o Basketball Reference não expõe um elemento de âncora confiável para `WebDriverWait` após a renderização — a espera fixa de 8 segundos é um trade-off pragmático entre confiabilidade e tempo de execução.

#### `uncomment_tables(raw_html)`

```python
comments = soup.find_all(string=lambda t: isinstance(t, Comment))
for c in comments:
    c.replace_with(BeautifulSoup(c, "lxml"))
```

O Basketball Reference envolve muitas tabelas em comentários HTML (`<!-- ... -->`), o que as torna invisíveis para parsers convencionais. Esta função localiza todos os comentários e os reinjeta no DOM como HTML real. Sem essa etapa, a maioria das tabelas do site simplesmente não existe no parse.

> **Detalhe técnico:** O método usado é `c.replace_with()` e não `soup.append()`. A partir da versão 4.13 do BeautifulSoup, `append()` retorna uma lista — usar `[0]` nela gera `IndexError` quando o resultado está vazio. O `replace_with()` é a forma correta e compatível com versões atuais.

#### `extract_table(soup, table_id)`

```python
table = soup.select_one(f"table#{table_id}")
df = pd.read_html(StringIO(str(table)))[0]
```

Localiza a tabela pelo ID no DOM descomentado e usa `pd.read_html()` para converter o HTML diretamente em DataFrame. O `StringIO` envolve a string para evitar o `FutureWarning` do pandas 2.x (que deprecia strings literais diretas para `read_html`).

#### Limpeza de dados no scraper

```python
df = df_raw[
    (df_raw["Player"] != "Player") &       # remove cabeçalhos repetidos
    (df_raw["Player"] != "League Average") # remove linha de média da liga
].drop(columns=["Rk", "Awards"], errors="ignore")
```

O Basketball Reference repete a linha de cabeçalho a cada 20 linhas para facilitar a leitura humana. A coluna `Awards` contém vírgulas internas (`"MVP-1,AS,NBA1"`), o que quebra o parser CSV do dbt. A coluna `Rk` é um índice visual sem valor analítico.

#### Renomeação de colunas para compatibilidade SQL

```python
COLUMN_RENAME = {
    "FG%": "fg_pct",
    "3P":  "three_p",
    "3PA": "three_pa",
    "W/L%": "wl_pct",
    ...
}
df = df.rename(columns=COLUMN_RENAME)
```

Colunas com `%`, `/` ou iniciadas por número são identificadores inválidos em SQL. O dbt tenta criar uma tabela com esses nomes e falha com erro interno (`list index out of range`) durante a geração do DDL. A renomeação acontece no scraper — antes de salvar o CSV — para que o banco nunca precise lidar com esses nomes.

---

### Etapa 2 — Carga (dbt seed)

```bash
dbt seed --profiles-dir .dbt
```

O dbt lê os CSVs de `basket_dbt/seeds/`, infere os tipos de dados com a biblioteca `agate` e gera automaticamente um `CREATE TABLE` + `INSERT` no schema `analytics_raw` do PostgreSQL. A configuração `+quote_columns: true` em `dbt_project.yml` garante que nomes de colunas sejam sempre escapados com aspas duplas no SQL gerado.

```yaml
seeds:
  +encoding: utf-8
  +quote_columns: true
  +schema: raw
```

O schema final no banco é `analytics_raw` (prefixo do projeto `analytics` + sufixo `raw` definido no seed config).

---

### Etapa 3 — Transformação (dbt run)

```bash
dbt run --profiles-dir .dbt
```

O dbt executa os modelos SQL em `models/staging/`, criando views no mesmo schema `analytics_raw`. Cada modelo lê de uma seed via `{{ ref('nome_da_seed') }}` — a função `ref()` é o mecanismo central do dbt para declarar dependências entre modelos, habilitando linhagem de dados automática e execução na ordem correta.

#### `stg_players.sql` — Dimensão de Jogadores

```sql
select
  trim("Player")                           as player_name,
  upper(trim("Team"))                      as team,
  upper(trim("Pos"))                       as position,
  nullif(trim("Age"::text), '')::integer   as age
from {{ ref('players') }}
where trim("Player") != 'Player'
```

**O que faz:** Seleciona as colunas de identificação dos 735 jogadores ativos na temporada 2024-25.

**Padrões aplicados:**
- `trim()`: Remove espaços em branco que podem vir do CSV
- `upper()`: Normaliza strings de categoria (posição, time) para maiúsculas — evita duplicatas como `"pf"` e `"PF"`
- `nullif(..., '')::integer`: Converte age para inteiro, tratando strings vazias como `NULL` em vez de gerar erro de cast
- `where trim("Player") != 'Player'`: Filtra as linhas de cabeçalho repetido que o Basketball Reference insere a cada 20 linhas na tabela HTML

#### `stg_players_stats.sql` — Fato de Estatísticas

```sql
select
  trim("Player")                                  as player_name,
  nullif(trim("G"::text),  '')::integer           as games_played,
  nullif(trim("MP"::text), '')::numeric(6,1)      as minutes_per_game,
  nullif(trim("fg_pct"::text), '')::numeric(5,3)  as fg_pct,
  ...
from {{ ref('players_stats') }}
where trim("Player") != 'Player'
```

**O que faz:** Transforma as 735 linhas de médias por jogo, fazendo cast explícito de cada coluna para o tipo correto.

**Padrões aplicados:**
- `numeric(p, s)`: Precisão controlada por coluna — `numeric(6,1)` para minutos, `numeric(5,3)` para percentuais (ex: `.519`). Evita que o PostgreSQL armazene valores com precisão arbitrária
- Cast via `::type`: Sintaxe idiomática do PostgreSQL, mais legível que `CAST(... AS ...)`
- Cada coluna recebe um alias semântico (`fg_per_game`, `assists_per_game`) em vez de nomes abreviados da fonte — a camada de staging é o lugar certo para essa tradução
- Jogadores trocados entre times aparecem com múltiplas linhas na fonte (uma por time + uma linha `TOT`). O modelo mantém essa granularidade intacta; a agregação fica para a camada enriched

#### `stg_team.sql` — Dimensão de Times

```sql
select * from {{ ref('team') }}
```

Modelo passthrough intencional — os dados já chegam limpos do scraper (com `wl_pct` renomeado). A lógica de selecionar apenas times ativos e criar a dimensão definitiva de franquias ficará na camada enriched (`dim_team`), que está planejada para a próxima fase do projeto.

---

## Configuração do Projeto

### Pré-requisitos

- Docker Desktop (para o PostgreSQL)
- Python 3.12+
- Chromium e ChromeDriver (instalados via snap no Linux/WSL)

### Setup

```bash
# 1. Clonar o repositório
git clone https://github.com/henriquegilles/NBA_Analisys.git
cd NBA_Analisys

# 2. Criar e ativar o ambiente virtual
python3 -m virtualenv .venv
source .venv/bin/activate

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Iniciar o PostgreSQL (Docker Desktop)
# Subir container postgres:latest com porta 5432 e banco 'nba'

# 5. Rodar o pipeline completo
dbt seed --profiles-dir .dbt   # carrega os CSVs
dbt run --profiles-dir .dbt    # executa os modelos
dbt test --profiles-dir .dbt   # valida os dados
```

### Atualizar os dados de origem

Execute os notebooks na seguinte ordem:

```
scraping/players/players.ipynb      → basket_dbt/seeds/players.csv
scraping/stats/stats.ipynb          → basket_dbt/seeds/players_stats.csv
scraping/teams/teams_scrap.ipynb    → basket_dbt/seeds/team.csv
scraping/contracts/nba_contracts.ipynb → basket_dbt/seeds/contracts.csv
```

Depois, rode `dbt seed --full-refresh` para recarregar os dados.

---

## Estado Atual e Próximos Passos

### O que está funcionando

| Componente | Status | Dados carregados |
|---|---|---|
| Scraper de jogadores | ✅ | 735 jogadores (2024-25) |
| Scraper de estatísticas | ✅ | 735 linhas de médias por jogo |
| Scraper de times | ✅ | 87 franquias históricas |
| `stg_players` | ✅ | View com tipagem correta |
| `stg_players_stats` | ✅ | View com 25 métricas por jogador |
| `stg_team` | ✅ | View com histórico de franquias |

### Próximas etapas planejadas

- **Camada Enriched:** Criar `dim_player`, `dim_team` e `fact_player_stats` com lógica de negócio (ex: classificar posições, calcular eficiência)
- **Contratos:** Integrar `nba_contracts.ipynb` ao pipeline e criar `dim_salary`
- **Testes dbt:** Adicionar testes de unicidade e not-null nos modelos de staging
- **Análises:** Queries de ranking (top scorers, eficiência ofensiva/defensiva) como primeiro entregável analítico
- **Orquestração:** Automatizar a atualização com Airflow ou cron job

---

## Decisões de Arquitetura

### Separação em camadas (staging → enriched)

A arquitetura segue o padrão de camadas do dbt, onde cada camada tem uma responsabilidade clara:

- **Seeds (raw):** Dados exatamente como vieram da fonte, sem transformações
- **Staging:** Uma transformação por fonte — tipagem correta, normalização de strings, filtro de linhas inválidas. Sem joins, sem lógica de negócio
- **Enriched (planejado):** Joins, agregações, regras de negócio. É aqui que `dim_player` e `fact_player_stats` serão construídos

Essa separação permite que cada camada seja testada e evoluída de forma independente.

### Views em vez de tables no staging

Os modelos de staging são materializados como views (`+materialized: view`). O dado já está persistido nas seeds (tabelas físicas). A view garante que a staging sempre reflita o estado atual das seeds sem duplicar armazenamento. Quando a camada enriched for criada, ela usará `table` para otimizar a performance de queries analíticas.

### Schema único `analytics_raw`

Seeds e views de staging compartilham o mesmo schema. A separação definitiva em `analytics_staging` e `analytics_enriched` acontecerá quando a camada enriched for implementada — evitando configuração prematura de infraestrutura.

---

## Autor

**Henrique** — Engenheiro de Dados em formação, com background em TI e foco em pipelines de dados com Python, dbt e SQL.

[GitHub](https://github.com/henriquegilles) | [LinkedIn](#)
