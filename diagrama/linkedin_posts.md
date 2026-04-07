# Posts LinkedIn — Aprendizados Reais com dbt

Série baseada no projeto NBA Analytics (dbt Core + PostgreSQL + Python).
Cada post é uma situação real que encontrei durante o desenvolvimento.

---

## POST 1 — O bug silencioso que os testes encontraram

Trabalhando no meu pipeline de dados da NBA, rodei o dbt e tudo compilou sem erro.

Mas quando executei os testes de qualidade... 81 duplicatas inesperadas.

O Basketball Reference mudou a nomenclatura para jogadores trocados de time:
— Antes usava "TOT" (Total)
— Agora usa "2TM", "3TM" conforme o número de times

Sem os testes, esses dados estariam errados em produção e ninguém perceberia.

A correção foi simples:

```sql
where team_abbr = 'TOT'
   or team_abbr ~ '^\d+TM$'
```

Uma linha de regex. Mas só cheguei nela porque os testes falharam e me apontaram o problema.

Testes de dados não são burocracia. São a única coisa que detecta quando a fonte muda silenciosamente.

No dbt, declarar um teste de unicidade leva 2 linhas de YAML. O custo de não ter é bem maior.

---

#dbt #DataEngineering #DataQuality #SQL

---
---

## POST 2 — Por que separo meu projeto dbt em 3 camadas

Quando comecei a usar dbt, coloquei toda a lógica no mesmo modelo. Funcionou por um tempo.

Depois de refatorar o projeto, adotei a separação em 3 camadas e entendi por que ela existe:

**Staging** → só limpeza. Renomear colunas, corrigir tipos, filtrar linhas inválidas. Nenhuma regra de negócio.

**Intermediate** → regras de negócio reutilizáveis. No meu caso: de-duplicar jogadores trocados de time, que aparecem múltiplas vezes na fonte.

**Marts** → o modelo dimensional final. As tabelas que analistas vão consultar.

O princípio que mudou minha forma de pensar:

**Se a fonte de dados mudar, só a staging precisa mudar.**

Intermediate e marts confiam nos contratos da staging — nomes de colunas e tipos estáveis. Uma mudança no Basketball Reference não quebra 5 modelos ao mesmo tempo.

Cada camada tem uma responsabilidade única e imutável.

É a mesma ideia do princípio de responsabilidade única do código — aplicada a modelos SQL.

---

#dbt #DataEngineering #DataModeling #SoftwareEngineering

---
---

## POST 3 — ref() é mais do que um atalho de nome

No dbt, quando você escreve:

```sql
select * from {{ ref('stg_bbr__players') }}
```

Parece só uma forma de referenciar uma tabela. Mas tem muito mais acontecendo.

O dbt usa cada ref() para construir o grafo de dependências do projeto inteiro.

Resultado prático:
— Ele sabe que não pode criar dim_player antes de stg_bbr__players existir
— Ele paraleliza automaticamente os modelos que não dependem um do outro
— Se você renomear um modelo, ele encontra todos os lugares que precisam atualizar

Eu nunca precisei escrever um script de orquestração dizendo "roda A, depois B, depois C e D em paralelo". O dbt calculou isso a partir das dependências que já estavam no código.

Isso é o que separa dbt de uma pasta com arquivos SQL numerados (01_staging.sql, 02_marts.sql...).

A ordem de execução emerge do código, não de um arquivo de configuração separado.

---

#dbt #DataEngineering #DAG #SQL #DataPipeline

---
---

## POST 4 — Seeds: quando CSV vira camada de dados com qualidade garantida

No meu projeto, os dados chegam como CSV (scraping do Basketball Reference).

A opção óbvia era fazer um script Python que carrega direto no banco. Funcionaria.

Mas escolhi usar dbt seed. A diferença:

Com seed, os CSVs entram no DAG do dbt. Isso significa:
— Os modelos que dependem dos dados sabem que precisam esperar o seed terminar
— Posso documentar as colunas no schema.yml como faço com qualquer modelo
— Posso rodar testes de qualidade já na camada mais crua dos dados
— Se o CSV mudar, dbt seed recria a tabela automaticamente

É uma linha de configuração no dbt_project.yml:

```yaml
seeds:
  nba_analytics:
    +schema: raw
    +quote_columns: true
```

E os dados caem em um schema separado (analytics_raw), isolados dos modelos transformados.

Parece detalhe. Mas quando o pipeline cresce, ter a ingestão dentro do mesmo grafo de dependências evita uma categoria inteira de bugs de ordem de execução.

---

#dbt #DataEngineering #DataPipeline #ELT

---
---

## POST 5 — O problema dos nomes de coluna que SQL não aceita

Ao conectar meu pipeline ao Basketball Reference, encontrei um problema clássico de dados reais:

Os nomes de colunas do site são inválidos em SQL.

```
FG%    → % é operador em SQL
3P     → identificador não pode começar com número
eFG%   → combina os dois problemas
W/L%   → / também é operador
```

Tentativa 1: usar aspas duplas no SQL para contornar. Funciona, mas vira poluição visual em todo arquivo que referencia essas colunas.

Solução definitiva: renomear na fonte, antes de salvar o CSV.

```python
RENAME = {
    "FG%": "fg_pct",
    "3P":  "three_p",
    "3P%": "three_p_pct",
    "eFG%": "efg_pct",
}
df = df.rename(columns=RENAME)
```

O CSV chega limpo. O dbt seed carrega sem problema. Todos os modelos downstream usam nomes legíveis.

Aprendizado: problemas de qualidade de dados devem ser resolvidos o mais próximo possível da fonte, não acumulados como débito técnico nas camadas seguintes.

---

#DataEngineering #dbt #Python #DataQuality #SQL

---
---

## POST 6 — View ou Table? A escolha que afeta performance e custo

No dbt, você escolhe como cada modelo é materializado no banco.

Fiquei um tempo usando table para tudo. Funcionava, mas estava desperdiçando recursos.

A regra que adotei:

**VIEW** para staging e intermediate:
— Não ocupam espaço em disco
— Executam a query na hora da consulta
— Perfeito para camadas que são raramente consultadas diretamente
— Mudam com frequência (se a fonte mudar, a view reflete automaticamente)

**TABLE** para marts:
— Dados persistidos fisicamente
— Consulta rápida — analistas não esperam a query rodar do zero
— É o que dashboards e notebooks acessam

No dbt_project.yml:

```yaml
staging:
  +materialized: view
intermediate:
  +materialized: view
marts:
  +materialized: table
```

Três linhas que definem o comportamento de todos os modelos de cada camada.

Existe ainda o tipo **incremental** (processa só registros novos) que uso quando o volume cresce. Mas esse fica para outro post.

---

#dbt #DataEngineering #PostgreSQL #DataModeling #SQL

---
---

## POST 7 — Credenciais no código: um erro que não pode ir para o GitHub

No início do projeto, as credenciais do banco estavam fixas no profiles.yml:

```yaml
host: localhost
user: postgres
password: postgres123
```

Funcionava. Mas ia para o repositório junto com o código.

A correção é usar env_var() — a função nativa do dbt para ler variáveis de ambiente:

```yaml
host:     "{{ env_var('DBT_HOST', 'localhost') }}"
user:     "{{ env_var('DBT_USER', 'postgres') }}"
password: "{{ env_var('DBT_PASSWORD', 'postgres') }}"
```

O segundo argumento é o fallback para desenvolvimento local. Em produção, as variáveis de ambiente são definidas no servidor sem tocar no código.

O arquivo profiles.yml vai para o .gitignore. No repositório fica só um profiles.yml.example com os nomes das variáveis e sem valores reais.

É o padrão dos 12 fatores aplicado a pipelines de dados.

Parece básico. Mas é exatamente o tipo de coisa que revisores técnicos verificam primeiro.

---

#dbt #DataEngineering #Security #BestPractices #DevOps

---
---

## POST 8 — O dado que parecia certo mas estava duplicado

Ao analisar os dados de jogadores no meu pipeline, os números pareciam normais.

Mas havia um problema escondido: jogadores trocados de time apareciam múltiplas vezes.

Um jogador que passou por 3 times tinha 4 linhas:
- Uma por time (3 linhas)
- Uma com o total da temporada (1 linha)

Se eu somasse os jogos sem tratar isso: 220 jogos em uma temporada de 82.

A solução foi criar uma camada intermediate específica para resolver isso:

```sql
traded_players as (
    select distinct player_name
    from players
    where team_abbr ~ '^\d+TM$'  -- 2TM, 3TM, 4TM...
),

deduped as (
    select p.*
    from players p
    left join traded_players t using (player_name)
    where t.player_name is null   -- não foi trocado: mantém
       or p.team_abbr ~ '^\d+TM$' -- foi trocado: mantém só o agregado
)
```

Toda camada downstream usa esse modelo. A lógica está em um lugar, documentada, testada.

Dados que parecem certos são os mais perigosos. O problema não estava no código — estava na estrutura da fonte de dados.

---

#DataEngineering #dbt #DataQuality #SQL #DataModeling

---
---

## POST 9 — Por que ELT substituiu ETL no pipeline moderno

Quando comecei a estudar engenharia de dados, aprendi ETL: extrair, transformar, carregar.

No meu projeto adotei ELT — e a diferença importa.

**ETL**: transforma os dados antes de carregar no banco. Era necessário quando armazenamento era caro e você não queria guardar dado bruto.

**ELT**: carrega os dados brutos primeiro, transforma dentro do banco. Possível com o barateamento de storage e aumento do poder computacional dos bancos modernos.

No meu caso:
1. Scrapers Python extraem do Basketball Reference e salvam CSV (Extract)
2. dbt seed carrega o CSV no PostgreSQL sem transformação (Load)
3. dbt run transforma dentro do banco: staging → intermediate → marts (Transform)

A vantagem prática: se eu precisar de uma análise nova que não estava prevista, os dados brutos já estão no banco. Basta criar um novo modelo dbt apontando para o raw.

No ETL tradicional, eu teria que voltar para a fonte, re-extrair e re-transformar tudo.

O dbt é fundamentalmente uma ferramenta ELT. Entender isso muda como você projeta o pipeline inteiro.

---

#DataEngineering #dbt #ELT #ETL #DataPipeline

---
---

## POST 10 — Documentação que ninguém precisa atualizar manualmente

Um dos maiores problemas em times de dados: documentação desatualizada.

O modelo foi alterado, a coluna foi renomeada, mas o Confluence ainda mostra o nome antigo. Semanas depois alguém consome dado errado.

No dbt, a documentação fica no mesmo arquivo YAML que define os testes:

```yaml
models:
  - name: fct_player_season_stats
    description: >
      Grain: uma linha por jogador por temporada.
      Stats per-game conforme publicado pelo Basketball Reference.
    columns:
      - name: points_per_game
        description: Média de pontos por jogo na temporada
        data_tests:
          - not_null
```

Quando você roda dbt docs generate, ele lê esses YAMLs e gera um site estático com:
— Descrição de cada modelo e coluna
— O grafo de dependências completo (quem depende de quem)
— Os resultados dos testes

E com GitHub Actions configurado, esse site é publicado automaticamente no GitHub Pages a cada push em master.

Se a coluna mudar de nome, você atualiza o YAML. A documentação é atualizada no próximo deploy.

Não é uma wiki separada. É o código documentando a si mesmo — e publicando sozinho.

---

#dbt #DataEngineering #Documentation #DataQuality #GitHubActions

---
