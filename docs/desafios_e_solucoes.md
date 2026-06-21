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

## 10. Cloudflare bypassado com `selenium-stealth`

**Sintoma:**
Todos os scrapers retornavam `Title: Um momento…` (Cloudflare challenge page) mesmo com
Selenium headless padrão.

**Causa:**
O Cloudflare detecta o Chrome headless pela presença de propriedades JavaScript como
`navigator.webdriver = true`, ausência de plugins, e fingerprint de GPU. O Selenium padrão
não oculta nenhuma dessas assinaturas.

**Solução aplicada:**
Instalado `selenium-stealth` e integrado ao `common/browser.py`:
```python
from selenium_stealth import stealth
stealth(driver, languages=["en-US","en"], vendor="Google Inc.",
        platform="Win32", webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine", fix_hairline=True)
```
Também adicionado `--disable-blink-features=AutomationControlled` e removidas as opções
`enable-automation` e `useAutomationExtension` para reforçar a camuflagem.

**Resultado:** BBR retornou páginas reais para todos os scrapers após a mudança.

---

## 11. IDs de tabelas BBR renomeados — scrapers quebraram

**Sintoma:**
```
ValueError: Table #contracts not found in page.
ValueError: Table #advanced_stats not found in page.
ValueError: Table #pgl_basic not found in page.
```

**Causa:**
O Basketball Reference renomeou vários IDs de tabela HTML entre as versões do site:

| Scraper | ID antigo | ID novo |
|---|---|---|
| `contracts.py` | `contracts` | `player-contracts` |
| `advanced_stats.py` (regular) | `advanced_stats` | `advanced` |
| `advanced_stats.py` (playoffs) | `advanced_stats` | `advanced_stats` ✓ (não mudou) |
| `player_gamelogs.py` | `pgl_basic` | `player_game_log_reg` |

**Solução aplicada:**
- `contracts.py`: `get_table(soup, "player-contracts")`
- `advanced_stats.py`: dicionário `TABLE_IDS = {"regular": "advanced", "playoffs": "advanced_stats"}`
- `player_gamelogs.py`: `TABLE_ID = "player_game_log_reg"`

**Prevenção futura:**
Ao receber `ValueError: Table #X not found`, inspecionar a página com:
```python
tables = soup.find_all("table")
print([t.get("id") for t in tables])
```

---

## 12. `data-stat="player"` renomeado para `data-stat="name_display"` no BBR

**Sintoma:**
```
Unique players com bbr_id: 0
```
O `players.py` gerava 733 linhas mas todos os `bbr_id` eram NaN.

**Causa:**
O `_extract_bbr_ids()` buscava células com `data-stat="player"` para extrair o atributo
`data-append-csv` (que contém o `bbr_id` real). O BBR renomeou esse atributo para
`data-stat="name_display"`.

**Solução aplicada:**
```python
# Antes:
for td in table.find_all("td", {"data-stat": "player"}):
# Depois:
for td in table.find_all("td", {"data-stat": "name_display"}):
```

**Prevenção futura:**
Ao ver todos os `bbr_id` como NaN após scraping, verificar com:
```python
row = table.find("tbody").find("tr")
for td in row.find_all("td")[:5]:
    print(td.get("data-stat"), td.get("data-append-csv"))
```

---

## 13. Colunas da tabela de gamelogs renomeadas no BBR

**Sintoma:**
Todos os 582 jogadores retornavam "no data" no `player_gamelogs.py`.

**Causa:**
Além do ID da tabela (`pgl_basic` → `player_game_log_reg`), as colunas foram renomeadas:

| Campo | Nome antigo | Nome novo |
|---|---|---|
| Time do jogador | `Tm` | `Team` |
| Data do jogo | `Date` | `Date` (igual) |
| Resultado | (derivado) | `Result` |
| Jogo na carreira | (não existia) | `Gcar` |
| Jogo no time | `G` | `Gtm` |

**Solução aplicada:**
Atualizado o dicionário `RENAME` em `player_gamelogs.py` para mapear os nomes novos.
Adicionado `"Gcar"` e `"Gtm"` à lista de colunas a descartar.

---

## 14. Chrome crashou no meio do scraping de gamelogs — dados perdidos

**Sintoma:**
```
selenium.common.exceptions.WebDriverException: Message: tab crashed
  (Session info: chrome=147.0.7727.55)
```
O scraper falhou no jogador 469/582 após ~30 minutos. Como os dados eram acumulados em
memória (`frames = []`) e escritos só no final, todos os 468 jogadores já processados foram perdidos.

**Causa:**
Sessões Chrome de longa duração acumulam memória. Com 582 páginas e 3s de sleep por página
(~30 minutos), o processo Chrome atingiu o limite de memória disponível no WSL.

**Solução aplicada:**
Refatorado `player_gamelogs.py` com três mecanismos:
1. **Escrita incremental** — cada jogador é gravado no CSV assim que processado (`append` mode),
   eliminando o risco de perder dados em crash.
2. **Resume automático** — na reinicialização, lê os `bbr_id` já no CSV e pula esses jogadores.
3. **Restart periódico do driver** — a cada 150 jogadores, o Chrome é encerrado e reiniciado
   para liberar memória.

**Prevenção futura:**
Se `player_gamelogs.py` falhar no meio da execução, basta rodá-lo novamente — ele retoma
automaticamente de onde parou.

---

## 15. CSV corrompido por incompatibilidade de colunas entre placeholder e dados reais

**Sintoma:**
```
pandas.errors.ParserError: Error tokenizing data. C error: Expected 31 fields in line 3, saw 35
```
O scraper de gamelogs falhou ao tentar retomar a execução — o `pd.read_csv` do CSV existente lançou erro de parse.

**Causa:**
O arquivo `seeds/player_gamelogs.csv` foi criado originalmente como placeholder com 31 colunas.
Quando o scraper com salvamento incremental rodou pela primeira vez, usou `mode="a", header=False`
para não reescrever o cabeçalho — mas os dados reais do BBR têm 35 colunas (`2P`, `2PA`, `2P%`,
`eFG%` a mais). O arquivo ficou com cabeçalho de 31 colunas e linhas de 35 valores:
incompatível com qualquer `pd.read_csv` padrão.

**Solução aplicada:**
1. Deletado o CSV corrompido: `rm seeds/player_gamelogs.csv`
2. `_already_scraped_ids()` atualizado para usar `on_bad_lines="skip"` e filtrar o sentinel
   `_placeholder` dos IDs retornados.
3. O scraper recriou o CSV com o cabeçalho correto de 35 colunas na primeira escrita.

**Prevenção futura:**
Placeholders com colunas fixas são frágeis — ao mudar o schema do scraper, o placeholder precisa
ser regerado. Alternativamente, deletar o placeholder antes de rodar o scraper pela primeira vez
com dados reais garante que o CSV seja criado com o schema atual.

---

## 16. Desalinhamento de colunas no CSV de gamelogs (rows com `three_p_pct` ou `ft_pct` ausentes)

**Sintoma:**
```
column "season" is null para 1.047 linhas em fct_player_game_log
O valor de bbr_id aparecia na coluna minutes_decimal (ex: "durenja01")
```

**Causa:**
O scraper usa escrita incremental com `header=False` — cada jogador é acrescentado por posição,
sem referenciar o nome da coluna. Jogadores com 0 tentativas de 3 pontos não têm a coluna
`three_p_pct` na tabela BBR, então o DataFrame deles tem 34 colunas em vez de 35. Quando
acrescentado por posição ao CSV de 35 colunas, todas as colunas a partir de `three_p_pct` ficam
deslocadas uma posição para a esquerda. Uma vírgula extra ao final da linha mascarava o problema
fazendo a linha parecer completa ao pandas.

24 jogadores adicionais também tinham `ft_pct` ausente (0/0 lances livres), causando deslocamento
de 2 posições.

**Solução aplicada:**
Script Python de correção pós-fato:
1. Identificação das linhas afetadas: `season IS NULL` (o valor de season foi deslocado para
   além do número de colunas).
2. Para as 1.023 linhas com `three_p_pct` ausente: inserção de `None` na posição 12,
   deslocando o restante para a direita.
3. Para as 24 linhas com `three_p_pct` E `ft_pct` ausentes: segunda inserção de `None`
   na posição 18.
4. CSV resalvo com 26.611 linhas, todas corretamente alinhadas.

**Prevenção futura:**
Adicionar `df = df.reindex(columns=EXPECTED_COLUMNS)` antes de `_append_to_csv()` no scraper.
Isso garante que DataFrames com colunas ausentes sejam preenchidos com `NaN` antes de escrever,
em vez de deslocar colunas.

---

## 17. BBR mudou formato do `game_result` — parse de point_diff quebrou

**Sintoma:**
```
invalid input syntax for type integer: "109-119"
```
O modelo `dim_game` falhava ao tentar converter o point_diff.

**Causa:**
O BBR alterou o formato da coluna `game_result` de `"W (+12)"` / `"L (-5)"` (diferença entre
parênteses) para `"W, 128-110"` / `"L, 109-119"` (placar completo). A regex antiga extraía
somente dígitos, resultando em `"109-119"` — que não pode ser convertido para integer diretamente.

**Solução aplicada:**
Handler dual-formato em `stg_bbr__player_gamelogs.sql`:
```sql
case
    when trim("game_result") ~ '\([+-]?\d+\)' then
        (regexp_match(trim("game_result"), '\(([+-]?\d+)\)'))[1]::integer
    when trim("game_result") ~ '\d+-\d+' then
        (regexp_match(trim("game_result"), '(\d+)-(\d+)'))[1]::integer
        - (regexp_match(trim("game_result"), '(\d+)-(\d+)'))[2]::integer
    else null
end as point_diff
```

---

## 18. BBR usa `*` para titulares em `games_started` — cast para integer falhou

**Sintoma:**
```
invalid input syntax for integer: "*"
```

**Causa:**
O BBR marca jogadores titulares com `*` na coluna `GS` (games_started). A expressão
`nullif(trim(...), '')::integer` não lida com o caractere `*`.

**Solução aplicada:**
```sql
case when trim("games_started"::text) = '*' then 1 else 0 end as games_started
```

---

## 19. Nomes de colunas case-sensitive no PostgreSQL — colunas de stats não encontradas

**Sintoma:**
```
column "ft" does not exist
column "orb" does not exist
```

**Causa:**
O dbt seed preserva exatamente o case do cabeçalho CSV. As colunas `FT`, `FTA`, `ORB`, `DRB`,
`TRB`, `AST`, `STL`, `BLK`, `TOV`, `PF`, `PTS` ficam em maiúsculas no banco. O modelo de staging
referenciava `"ft"`, `"orb"` etc. em minúsculas.

**Solução aplicada:**
Atualizado `stg_bbr__player_gamelogs.sql` para usar as referências em maiúsculas:
`"FT"`, `"FTA"`, `"ORB"`, `"DRB"`, `"TRB"`, `"AST"`, `"STL"`, `"BLK"`, `"TOV"`, `"PF"`, `"PTS"`.

---

## 20. Valores não-numéricos em colunas de stats — jogadores suspensos

**Sintoma:**
```
invalid input syntax for type numeric: "Suspended"
```

**Causa:**
Quando um jogador está suspenso, o BBR preenche todas as colunas de stats (FG, FGA, PTS, etc.)
com a string `"Suspended"` em vez de valores numéricos. O `nullif(trim(...), '')::numeric` só
trata string vazia, não strings textuais.

**Solução aplicada:**
Substituição de `nullif(trim(...), '')::numeric` por uma expressão CASE com regex em todas as
colunas de stats em `stg_bbr__player_gamelogs.sql`:
```sql
(case when trim("PTS"::text) ~ '^-?[0-9]+\.?[0-9]*$' then trim("PTS"::text) end)::numeric(5,1)
```
Isso transforma qualquer valor não-numérico (Suspended, Inactive, Did Not Play, etc.) em NULL.

---

## 21. Colisões no `generate_id` — surrogate key duplicada em `fct_player_game_log`

**Sintoma:**
```
Failure in test unique_fct_player_game_log_game_player_key — Got 6 results
```
6 pares de `(bbr_id, game_date)` distintos geravam o mesmo hash de 8 dígitos.

**Causa:**
O macro `generate_id` usava `hashtext()` (32 bits) com módulo 90M → domínio de apenas 90 milhões
de valores. Com 26.611 linhas, o paradoxo do aniversário prevê ~4 colisões esperadas (calculado
como n²/2m = 26611²/180M ≈ 3,94). Os 6 observados são consistentes com a previsão.

**Solução aplicada:**
`generate_id` refatorado para delegar ao `dbt_utils.generate_surrogate_key`, que usa MD5 e retorna
um varchar de 32 chars. Domínio de 2^128 valores — colisões são matematicamente impossíveis para
os volumes deste projeto. As surrogate keys de todos os modelos passaram de `integer` para
`varchar`. Contratos atualizados em `_marts__models.yml`.

---

## 22. CI falhando após troca do `generate_id` para `dbt_utils`

**Sintoma:**
```
Run failed: dbt Docs - master (9502b5a)
```
O workflow de GitHub Actions falhou logo após o commit que migrou `generate_id` para
`dbt_utils.generate_surrogate_key`.

**Causa:**
`dbt_packages/` está no `.gitignore` — o diretório não é commitado no repositório. Em um ambiente
de CI limpo (fresh checkout), o `dbt_utils` não existe até que `dbt deps` seja executado. Os
workflows `ci.yml` e `docs.yml` não tinham esse passo, então qualquer macro de `dbt_utils`
falhava na compilação com erro de macro não encontrada.

**Solução aplicada:**
Adicionado o passo `dbt deps --profiles-dir .dbt` em ambos os workflows, antes de qualquer
comando dbt que use pacotes:
```yaml
- name: dbt deps
  run: dbt deps --profiles-dir .dbt
```

**Regra geral:**
Sempre que um novo pacote for adicionado ao `packages.yml`, verificar se os workflows de CI
têm o passo `dbt deps`. Sem ele, o CI passará localmente (onde `dbt_packages/` já existe)
mas falhará no runner do GitHub.

---

## 23. Postgres não sobe via `sudo service postgresql start` — nesta máquina é Docker

**Sintoma:**
`dbt debug` / qualquer comando dbt falha com `connection to server at "localhost"
(127.0.0.1), port 5432 failed: Connection refused`. O `sudo service postgresql start`
sugerido no CLAUDE.md pede senha e, mesmo com ela, não há serviço: não existe
`/etc/init.d/postgresql`, `psql` não está no PATH e não há cluster (`pg_lsclusters` ausente).

**Causa:**
O Postgres **não está instalado localmente** nesta WSL. O projeto roda o banco via
**Docker** (`docker-compose.yml`, imagem `postgres:17-alpine`, container `nba_postgres`).
A instrução `sudo service postgresql start` no CLAUDE.md é stale para esta máquina.

**Solução:**
```bash
docker compose up -d postgres
```
Se aparecer *"The command 'docker' could not be found in this WSL 2 distro"*, o binário
existe (`/mnt/c/Program Files/Docker/.../docker`) mas a **WSL Integration do Docker Desktop
está desligada** para esta distro. Ligar em: Docker Desktop → Settings → Resources →
WSL Integration → habilitar a distro → Apply & Restart. Depois `docker compose up -d postgres`.

**Nota para o agente:** subir o banco exige ação manual do usuário (sudo com senha ou
ligar a integração do Docker Desktop) — não é automatizável pela sessão. Peça ao usuário
para rodar `! docker compose up -d postgres` no prompt.

---

## 24. `dbt` no PATH é o dbt-fusion (sem postgres) — usar o do `.venv`

**Sintoma:**
`dbt parse` / `dbt run` falha com
`[InvalidConfig (dbt1005)]: The 'postgres' adapter is not yet supported by dbt Fusion.
Supported adapters: snowflake, bigquery, databricks, redshift`. Parece config quebrada,
mas o `profiles.yml` está correto.

**Causa:**
Há **dois `dbt` instalados** nesta máquina:
- `~/.local/bin/dbt` → **dbt-fusion 2.0** (reescrita em Rust; ainda **não suporta postgres**).
- `.venv/bin/dbt` → **dbt-core 1.9.10 + adapter postgres 1.9.1** (o correto pro projeto).

Sem o venv ativado, o `~/.local/bin` vence no PATH e `dbt` resolve pro **fusion**, que
rejeita o adapter postgres. Cada shell novo (inclusive cada chamada de ferramenta do
agente) começa **sem** o `source .venv/bin/activate`.

**Solução:**
Ativar o venv (`source .venv/bin/activate`) **ou** prefixar o binário explicitamente:
```bash
.venv/bin/dbt parse --profiles-dir .dbt     # dbt-core 1.9.10, registra adapter postgres
```
Confirmar qual está ativo: `dbt --version` deve dizer `Core: installed 1.9.10` e
`Registered adapter: postgres`. Se aparecer `dbt-fusion`, é o errado.

**Nota para o agente:** em chamadas Bash que não herdam o `activate`, **sempre** prefixe
`.venv/bin/dbt` (e `.venv/bin/python` — o `python` cru também não existe no PATH base).

---

## 25. BBR mudou o cabeçalho de 2 níveis do draft — `read_html`+flatten quebrou (D-30)

**Sintoma:**
Ao re-raspar o draft (`draft.py`) para capturar o `bbr_id`, as colunas saíram
erradas: `Round 1_Player`, `Round 1_College`, `Shooting_FG%`, `Advanced_WS` — e
**nenhum `player_name` nem `bbr_id`**. Como o bloco de captura do slug era
protegido por `if "player_name" in df.columns`, ele simplesmente não rodava.

**Causa:**
A BBR mudou os rótulos do cabeçalho de duas camadas da tabela `#stats` do draft.
O `pd.read_html` + `_flatten_columns` montava nomes como `<grupo>_<coluna>`, e o
`RENAME` esperava os grupos antigos (`Totals_FG%`, `Per Game_PTS`, `WS`). Com os
grupos novos (`Round 1`, `Shooting`, `Advanced`), o rename não casava nada — a
coluna "Player" virou `Round 1_Player`. Mesma classe do problema #11/#12 (BBR
renomeia HTML periodicamente).

**Solução:**
Abandonar `read_html`+flatten e parsear a tabela por **`data-stat`** (como o
`college.py` já faz) — nomes estáveis e SQL-safe, imunes a mudança de
superheader, e o `<a href>` da célula `player` dá o `bbr_id` direto. Mapa atual
(inspecionado 2026-06-21): `pick_overall, team_id, player, college_name,
seasons, g, mp, pts, trb, ast, fg_pct, fg3_pct, ft_pct, mp_per_g, pts_per_g,
trb_per_g, ast_per_g, ws, ws_per_48, bpm, vorp`.

**Pegadinha relacionada (mesmo bloco):** na **página do jogador** a linha de
total da tabela `per_game_stats` não se chama mais "Career" e sim **"N Yrs"**
(ex.: "2 Yrs", "14 Yrs"). O `nba_careers.py` casa ambos via
`^(career|\d+\s+yrs?)$`. O total de jogos (`g`) não aparece nessa linha — fica
NULL no seed; o `nba_career_games` usado de fato vem do `draft`.

**Nota para o agente:** preferir **`data-stat`** a `read_html` em qualquer parser
de BBR novo — o "Resumo" abaixo já apontava isso para o `bbr_id`.

---

## Resumo de comandos de recuperação

| Situação | Comando |
|---|---|
| Novos pacotes adicionados ao `packages.yml` | `dbt deps --profiles-dir .dbt` |
| Colunas adicionadas/removidas de um CSV seed | `dbt seed --profiles-dir .dbt --full-refresh` |
| Schema de um modelo mart mudou | `dbt run --profiles-dir .dbt --full-refresh --select <modelo>` |
| BBR bloqueado por Cloudflare | Instalar `selenium-stealth` e aplicar no `build_driver()` |
| Tabela BBR não encontrada | Inspecionar IDs com `[t.get("id") for t in soup.find_all("table")]` |
| `bbr_id` todos NaN após scraping | Verificar `data-stat` do elemento player — pode ter mudado |
| Chrome tab crashed no scraper | Reiniciar o script — resume automaticamente pelo CSV parcial |
| Surrogate key corrompida (colisão de IDs) | `dbt run --profiles-dir .dbt --full-refresh` |
| Testes de FK falhando | Verificar abreviações em `team_info.csv` vs scraped data |
| `Connection refused` no `dbt debug` (porta 5432) | `docker compose up -d postgres` (não é serviço local — ver #23) |
| `postgres adapter not supported by dbt Fusion` | Usar `.venv/bin/dbt` (PATH resolve pro fusion — ver #24) |
