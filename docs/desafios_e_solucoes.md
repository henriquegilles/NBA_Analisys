# Desafios Técnicos e Soluções — NBA Analytics Pipeline

> Registro dos principais problemas encontrados durante o desenvolvimento e execução do pipeline.
> Serve como runbook para troubleshooting futuro e como documentação de decisões de design.

---

## 1. Cloudflare bloqueando o scraper do BBR

**Sintoma:**
```
Page title: <title>Um momento…</title>
HTML length: 31798
```
O scraper retornava uma página de challenge do Cloudflare (~31 KB) em vez da página com os dados.

**Causa:**
O Basketball Reference detectou o browser headless e serviu um challenge de bot (CAPTCHA/WAF).
Esse comportamento é intermitente — depende do horário, frequência de requisições e assinatura do
Chrome headless detectada pelo Cloudflare.

**Solução temporária aplicada:**
- Geração sintética de `bbr_id` seguindo a convenção BBR (`lastname[:5] + firstname[:2] + contador`),
  mapeada por nome único de jogador para manter consistência em jogadores trocados (múltiplas linhas).
- Adicionadas colunas `bbr_id` e `season` diretamente no `players.csv` existente via script Python.

**Solução definitiva (quando o scraper voltar a funcionar):**
```bash
cd src/scraping && python players.py
# Substitui os IDs sintéticos pelos reais do BBR.
# Depois rodar:
dbt seed --profiles-dir .dbt --full-refresh --select players
dbt run --profiles-dir .dbt
```

**Prevenção futura:**
Adicionar ao `common/browser.py`:
```python
page_title = BeautifulSoup(driver.page_source, "lxml").title
if page_title and "momento" in page_title.text.lower():
    raise CloudflareBlockedError("BBR retornou challenge page — tente novamente mais tarde.")
```

---

## 2. PostgreSQL inferindo tipo `integer` em colunas de CSVs placeholder

**Sintoma:**
```
Database Error: function pg_catalog.btrim(integer) does not exist
HINT: No function matches the given name and argument types.
```

**Causa:**
Os CSVs placeholder criados para seeds ausentes tinham apenas a linha de header (sem dados).
O dbt seed passa esses dados para o PostgreSQL, que — sem valores — infere `integer` como tipo
padrão para todas as colunas. Quando o staging model tenta `trim("Player")`, o PostgreSQL não
encontra a função `btrim(integer)`.

**Solução aplicada:**
Duas frentes simultâneas:
1. Adicionada linha dummy a cada CSV placeholder com valores string nas colunas-chave,
   garantindo que o PostgreSQL infira `text` corretamente.
2. Adicionado `column_types` no `seeds/schema.yml` para forçar o tipo nas colunas críticas:
```yaml
config:
  column_types:
    Player: varchar
    Tm: varchar
```

**Por que não basta a linha dummy?**
Colunas com valores NULL em todos os registros (ex: `college` no draft) ainda podem ser inferidas
como integer. O `column_types` no schema.yml é a solução definitiva e independente do conteúdo.

---

## 3. Schema desatualizado impede `dbt seed` sem `--full-refresh`

**Sintoma:**
```
Database Error: column "bbr_id" of relation "players" does not exist
```

**Causa:**
A tabela `analytics_raw.players` já existia no PostgreSQL com o schema antigo (sem `bbr_id`, sem
`season`). O comando `dbt seed` padrão usa `INSERT` e assume que o schema é idêntico ao CSV.
Quando o CSV tem colunas novas, o INSERT falha.

**Solução aplicada:**
```bash
dbt seed --profiles-dir .dbt --full-refresh
```
O `--full-refresh` faz DROP + CREATE da tabela antes do INSERT, garantindo que o schema seja
recriado a partir do CSV atual.

**Regra prática:**
Sempre usar `--full-refresh` ao:
- Adicionar ou remover colunas de um CSV seed
- Mudar o tipo de uma coluna
- Após instalar o `dbt_utils` pela primeira vez (mudança de projeto que invalida o parser parcial)

---

## 4. `dbt_utils` não instalado — pipeline não compilava

**Sintoma:**
```
Compilation Error
  dbt found 1 package(s) specified in packages.yml,
  but only 0 package(s) installed in dbt_packages.
  Run "dbt deps" to install package dependencies.
```

**Causa:**
O arquivo `packages.yml` foi criado declarando a dependência do `dbt_utils`, mas o comando
`dbt deps` não tinha sido executado — os pacotes não estavam em `dbt_packages/`.

**Solução aplicada:**
```bash
dbt deps --profiles-dir .dbt
```

**Prevenção futura:**
O `dbt deps` deve ser rodado uma vez após qualquer mudança no `packages.yml`.
Adicionado ao README como passo obrigatório do setup inicial:
```bash
dbt deps --profiles-dir .dbt   # installs dbt_utils package
```

---

## 5. Abreviações de times divergentes entre BBR e `team_info.csv`

**Sintoma:**
```
Failure in test relationships_dim_player_current_team_abbr__team_abbr__ref_dim_team_
  Got 59 results, configured to fail if != 0
```

**Causa:**
O BBR usa abreviações diferentes das adotadas por outras fontes para três times:

| Time | BBR (scrapers) | team_info.csv (antigo) |
|---|---|---|
| Brooklyn Nets | `BRK` | `BKN` |
| Charlotte Hornets | `CHO` | `CHA` |
| Phoenix Suns | `PHO` | `PHX` |

O `dim_player.current_team_abbr` vinha do BBR (ex: `CHO`), mas `dim_team.team_abbr` vinha do
`team_info.csv` (ex: `CHA`). O teste de FK detectou 59 jogadores sem time correspondente.

**Solução aplicada:**
Atualizado `seeds/team_info.csv` para usar as abreviações do BBR (fonte de verdade do projeto):
```
BRK,Brooklyn Nets,...
CHO,Charlotte Hornets,...
PHO,Phoenix Suns,...
```

**Regra prática:**
O BBR é a fonte de verdade para abreviações de time neste projeto. Qualquer referência estática
(`team_info.csv`) deve usar as abreviações BBR para manter a consistência dos JOINs.

---

## 6. `bbr_id` sintético com colisões para jogadores com nomes similares

**Sintoma:**
```
Failure in test unique_dim_player_bbr_id — Got 12 results
Failure in test unique_dim_player_player_key — Got 12 results
```

**Causa:**
A primeira versão do gerador sintético de `bbr_id` criava IDs por **linha** do CSV, não por
**jogador único**. Jogadores trocados (ex: Luka Dončić com linhas para `2TM`, `DAL` e `LAL`)
recebiam IDs diferentes por ocorrência. Além disso, jogadores com nomes muito similares (ex:
"Jordan Johnson" e "Jordan Jones") geravam o mesmo base-ID `johnjo`.

**Solução aplicada:**
1. Mapeamento por nome único antes de aplicar ao DataFrame:
   ```python
   unique_names = players["Player"].unique().tolist()
   id_map = make_bbr_id_map(unique_names)
   players["bbr_id"] = players["Player"].map(id_map)
   ```
2. Contador incremental por base para garantir unicidade:
   ```python
   base = (last[:5] + first[:2]).ljust(7, "0")[:7]
   counts[base] += 1
   mapping[name] = f"{base}{counts[base]:02d}"
   ```

**Nota importante:**
Os `bbr_id` sintéticos **não coincidem** com os do BBR. Quando o scraper funcionar novamente,
os IDs reais serão diferentes dos sintéticos, causando IDs "novos" no surrogate key.
Plano de migração: `dbt seed --full-refresh --select players && dbt run --full-refresh`.

---

## 7. Validação YAML quebrando por `:` dentro de parênteses sem aspas

**Sintoma:**
```
yaml.scanner.ScannerError: mapping values are not allowed here
  in "_marts__models.yml", line 299, column 54
```

**Causa:**
Descriptions no YAML sem aspas contendo `(ex: valor)` são interpretadas como mapeamento pelo
parser YAML. O padrão `(ex: 32.23)` quebra o parse porque `: ` dentro de uma string não-quoted
sinaliza uma nova chave de mapa.

**Solução aplicada:**
Envolver descriptions com `(ex: ...)` em aspas duplas:
```yaml
# QUEBRA:
description: Minutos jogados como decimal (ex: 32.23)

# CORRETO:
description: "Minutos jogados como decimal (ex: 32.23)"
```

**Prevenção futura:**
Qualquer string YAML que contenha `: ` (dois pontos + espaço) deve estar entre aspas.

---

## 8. Placeholder do draft com NULL nas colunas `draft_year` e `pick`

**Sintoma:**
```
Failure in test not_null_fct_draft_class_draft_year — Got 1 result
Failure in test not_null_fct_draft_class_pick — Got 1 result
```

**Causa:**
A linha dummy do `draft.csv` tinha `draft_year` e `pick` como NULL para não simular dados falsos.
O staging model filtrava apenas `player_name != ''`, mas não filtrava `draft_year IS NULL`.

**Solução aplicada:**
Adicionado filtro defensivo no `stg_bbr__draft.sql`:
```sql
where trim("player_name") != ''
  and "player_name" is not null
  and "draft_year" is not null  -- ← filtro adicionado
  and "pick" is not null        -- ← filtro adicionado
```
Essa mudança melhora a qualidade independente do placeholder — garante que linhas incompletas
do BBR (draft sem número de pick ou ano) nunca cheguem às marts.

---

## 9. `dbt run` não recria views ao mudar schema — usar `--full-refresh` em tabelas

**Sintoma:**
Mudanças no SQL de um modelo `materialized: view` são refletidas imediatamente no próximo
`dbt run`. Mas mudanças de schema em modelos `materialized: table` requerem `--full-refresh`
para que as novas colunas apareçam.

**Causa:**
`materialized: table` usa `CREATE TABLE IF NOT EXISTS` + `INSERT`. Se a coluna não existe na
tabela física, o INSERT falha. Views recriadas sempre com `CREATE OR REPLACE VIEW`.

**Solução aplicada:**
Usar `--full-refresh` após mudanças estruturais em marts:
```bash
dbt run --profiles-dir .dbt --full-refresh --select dim_player dim_team
```

---

## Resumo de comandos de recuperação

| Situação | Comando |
|---|---|
| Novos pacotes adicionados ao `packages.yml` | `dbt deps --profiles-dir .dbt` |
| Colunas adicionadas/removidas de um CSV seed | `dbt seed --profiles-dir .dbt --full-refresh` |
| Schema de um modelo mart mudou | `dbt run --profiles-dir .dbt --full-refresh --select <modelo>` |
| BBR bloqueado por Cloudflare | Aguardar e retentar; verificar título da página |
| Surrogate key corrompida (colisão de IDs) | `dbt run --profiles-dir .dbt --full-refresh` |
| Testes de FK falhando | Verificar abreviações em `team_info.csv` vs scraped data |
