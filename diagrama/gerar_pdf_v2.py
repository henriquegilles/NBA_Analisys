"""
Gerador do PDF v2 — NBA Analytics: Guia Completo + Novas Ferramentas.
Execução: python diagrama/gerar_pdf_v2.py
Saída:    diagrama/NBA_Analytics_Guia_Completo.pdf   (sobrescreve a versão anterior)
"""

import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    PageTemplate,
    Frame,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    PageBreak,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

# ── Paleta ────────────────────────────────────────────────────────────────────
ORANGE = colors.HexColor("#FF6B35")
DARK = colors.HexColor("#1A1A2E")
BLUE = colors.HexColor("#16213E")
LIGHT_BG = colors.HexColor("#F8F9FA")
GRAY = colors.HexColor("#6C757D")
GREEN = colors.HexColor("#28A745")
RED = colors.HexColor("#DC3545")
TEAL = colors.HexColor("#17A2B8")
PURPLE = colors.HexColor("#6F42C1")
DARK_GREEN = colors.HexColor("#155724")

OUTPUT = os.path.join(os.path.dirname(__file__), "NBA_Analytics_Guia_Completo.pdf")
W, H = A4


# ── Estilos ───────────────────────────────────────────────────────────────────
def make_styles():
    s = {}
    s["h1"] = ParagraphStyle(
        "h1",
        fontSize=20,
        textColor=DARK,
        fontName="Helvetica-Bold",
        spaceBefore=24,
        spaceAfter=8,
    )
    s["h2"] = ParagraphStyle(
        "h2",
        fontSize=15,
        textColor=ORANGE,
        fontName="Helvetica-Bold",
        spaceBefore=18,
        spaceAfter=6,
    )
    s["h3"] = ParagraphStyle(
        "h3",
        fontSize=12,
        textColor=BLUE,
        fontName="Helvetica-Bold",
        spaceBefore=12,
        spaceAfter=4,
    )
    s["body"] = ParagraphStyle(
        "body",
        fontSize=10,
        textColor=DARK,
        fontName="Helvetica",
        leading=16,
        spaceAfter=6,
        alignment=TA_JUSTIFY,
    )
    s["bullet"] = ParagraphStyle(
        "bullet",
        fontSize=10,
        textColor=DARK,
        fontName="Helvetica",
        leading=15,
        spaceAfter=3,
        leftIndent=16,
        alignment=TA_LEFT,
    )
    s["sub_b"] = ParagraphStyle(
        "sub_b",
        fontSize=9.5,
        textColor=DARK,
        fontName="Helvetica",
        leading=14,
        spaceAfter=2,
        leftIndent=32,
        alignment=TA_LEFT,
    )
    s["code"] = ParagraphStyle(
        "code",
        fontSize=8.5,
        textColor=colors.HexColor("#2D2D2D"),
        fontName="Courier",
        leading=12,
        spaceAfter=2,
        leftIndent=8,
        backColor=colors.HexColor("#F4F4F4"),
        borderPad=4,
    )
    s["callout"] = ParagraphStyle(
        "callout",
        fontSize=10,
        textColor=DARK,
        fontName="Helvetica",
        leading=15,
        spaceAfter=4,
        leftIndent=12,
        rightIndent=12,
        borderPad=6,
        backColor=colors.HexColor("#FFF3CD"),
    )
    s["tip"] = ParagraphStyle(
        "tip",
        fontSize=10,
        textColor=DARK_GREEN,
        fontName="Helvetica",
        leading=15,
        spaceAfter=4,
        leftIndent=12,
        rightIndent=12,
        borderPad=6,
        backColor=colors.HexColor("#D4EDDA"),
    )
    s["interview"] = ParagraphStyle(
        "interview",
        fontSize=10,
        textColor=DARK_GREEN,
        fontName="Helvetica-Bold",
        leading=15,
        spaceAfter=3,
        leftIndent=12,
        backColor=colors.HexColor("#D4EDDA"),
        borderPad=5,
    )
    s["interview_ans"] = ParagraphStyle(
        "interview_ans",
        fontSize=10,
        textColor=DARK,
        fontName="Helvetica",
        leading=15,
        spaceAfter=6,
        leftIndent=16,
        alignment=TA_JUSTIFY,
    )
    s["caption"] = ParagraphStyle(
        "caption",
        fontSize=8,
        textColor=GRAY,
        fontName="Helvetica-Oblique",
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    s["footer"] = ParagraphStyle(
        "footer", fontSize=8, textColor=GRAY, fontName="Helvetica", alignment=TA_CENTER
    )
    return s


S = make_styles()


# ── Helpers ───────────────────────────────────────────────────────────────────
def hr(color=ORANGE, t=1.5):
    return HRFlowable(width="100%", thickness=t, color=color, spaceAfter=6)


def sp(n=6):
    return Spacer(1, n)


def h1(t):
    return Paragraph(t, S["h1"])


def h2(t):
    return Paragraph(t, S["h2"])


def h3(t):
    return Paragraph(t, S["h3"])


def p(t):
    return Paragraph(t, S["body"])


def b(t):
    return Paragraph(f"• {t}", S["bullet"])


def bb(t):
    return Paragraph(f"– {t}", S["sub_b"])


def code(t):
    return Paragraph(t.replace("\n", "<br/>").replace("  ", "&nbsp;&nbsp;"), S["code"])


def callout(t):
    return Paragraph(t, S["callout"])


def tip(t):
    return Paragraph(t, S["tip"])


def iq(t):
    return Paragraph(f"🎯 Pergunta de entrevista: {t}", S["interview"])


def ia(t):
    return Paragraph(t, S["interview_ans"])


def section(title):
    return [sp(12), hr(ORANGE, 2), Paragraph(title, S["h1"]), hr(ORANGE, 0.5), sp(4)]


def ctable(data, widths, hbg=DARK, hfg=colors.white):
    style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), hbg),
            ("TEXTCOLOR", (0, 0), (-1, 0), hfg),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_BG, colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDDDDD")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]
    )
    return Table(data, colWidths=widths, style=style, hAlign="LEFT")


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(DARK)
    canvas.rect(0, 0, W, 1.2 * cm, fill=1, stroke=0)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.white)
    canvas.drawString(
        1.5 * cm,
        0.45 * cm,
        "NBA Analytics — Guia Completo · dbt + PostgreSQL + Dagster + Docker + CI/CD",
    )
    canvas.drawRightString(W - 1.5 * cm, 0.45 * cm, f"Página {doc.page}")
    canvas.restoreState()


# ══════════════════════════════════════════════════════════════════════════════
# CONTEÚDO
# ══════════════════════════════════════════════════════════════════════════════
def build_content():
    story = []

    # ── CAPA ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 2.5 * cm))
    capa = Table(
        [
            [
                Paragraph(
                    "<br/><b>NBA ANALYTICS</b><br/>"
                    "<font size=14 color='#FF6B35'>Pipeline de Engenharia de Dados — Guia Completo</font><br/>"
                    "<font size=10 color='#AAAAAA'>dbt Core · PostgreSQL · Python · Selenium · Dagster · Docker · GitHub Actions</font><br/><br/>",
                    ParagraphStyle(
                        "ct",
                        fontSize=26,
                        textColor=colors.white,
                        fontName="Helvetica-Bold",
                        alignment=TA_CENTER,
                    ),
                )
            ]
        ],
        colWidths=[W - 4 * cm],
    )
    capa.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), DARK),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 24),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 24),
            ]
        )
    )
    story.append(capa)
    story.append(sp(20))

    itens = [
        [
            "🔧 dbt Core — conceitos e camadas",
            "🐳 Docker Compose — ambiente reproduzível",
        ],
        ["📁 Cada arquivo e pasta explicado", "⚙️  Dagster — orquestração e assets"],
        ["🧠 Regras de negócio implementadas", "🔄 GitHub Actions — CI/CD automático"],
        [
            "🧪 Testes de qualidade de dados",
            "💼 Guia completo de entrevista Pleno/Sênior",
        ],
    ]
    grid = Table(itens, colWidths=[(W - 4 * cm) / 2] * 2)
    grid.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("TEXTCOLOR", (0, 0), (-1, -1), DARK),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDDDDD")),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_BG, colors.white]),
            ]
        )
    )
    story.append(grid)
    story.append(PageBreak())

    # ── PARTE 1: VISÃO GERAL ─────────────────────────────────────────────────
    story += section("PARTE 1 — Visão Geral do Projeto")

    story.append(h2("1.1 O que é este projeto"))
    story.append(
        p(
            "Pipeline de dados end-to-end para análise de estatísticas da NBA. Extrai dados do "
            "Basketball Reference via Selenium, armazena em PostgreSQL, transforma com dbt Core "
            "seguindo arquitetura em três camadas, orquestra com Dagster e valida com GitHub Actions CI."
        )
    )
    story.append(sp(6))

    story.append(h2("1.2 Stack tecnológica completa"))
    stack = [
        ["Camada", "Ferramenta", "Versão", "Função"],
        [
            "Extração",
            "Python + Selenium",
            "4.31",
            "Web scraping do Basketball Reference",
        ],
        ["Armazenamento", "PostgreSQL", "17", "Data warehouse local"],
        ["Ambiente", "Docker Compose", "v2", "Banco reproduzível em qualquer máquina"],
        ["Transformação", "dbt Core", "1.9.10", "Modelos SQL em 3 camadas"],
        ["Orquestração", "Dagster", "latest", "Agendamento, assets, observabilidade"],
        ["Qualidade", "dbt tests (YAML)", "—", "26 testes declarativos automatizados"],
        ["CI/CD", "GitHub Actions", "—", "Compile + seed + run + test em cada PR"],
        ["Docs", "dbt docs + GH Pages", "—", "Documentação publicada automaticamente"],
    ]
    story.append(ctable(stack, [2.5 * cm, 3.5 * cm, 1.8 * cm, 9.2 * cm]))
    story.append(sp(8))

    story.append(h2("1.3 Fluxo completo do pipeline"))
    story.append(
        code(
            "Basketball Reference\n"
            "      │\n"
            "      │  Selenium (headless Chromium) — src/scraping/\n"
            "      ▼\n"
            "  seeds/*.csv  (camada raw)\n"
            "      │\n"
            "      │  dbt seed  →  analytics_raw.*\n"
            "      ▼\n"
            "  models/staging/bbr/  →  analytics_staging.*   (views — limpeza)\n"
            "      │\n"
            "      │  dbt run\n"
            "      ▼\n"
            "  models/intermediate/  →  analytics_intermediate.*  (views — regras de negócio)\n"
            "      │\n"
            "      ▼\n"
            "  models/marts/  →  analytics_marts.*  (tables — dim_* e fct_*)\n"
            "      │\n"
            "      │  dbt test  →  26 testes de qualidade\n"
            "      ▼\n"
            "  Dagster UI  →  observabilidade, agendamento, histórico de runs\n"
            "  GitHub Actions  →  CI automático a cada PR"
        )
    )
    story.append(PageBreak())

    # ── PARTE 2: DBT ─────────────────────────────────────────────────────────
    story += section("PARTE 2 — dbt Core: Conceitos e Camadas")

    story.append(h2("2.1 O que é dbt e por que ele existe"))
    story.append(
        p(
            "<b>dbt (data build tool)</b> é uma ferramenta que permite escrever transformações de dados "
            "em SQL puro, com dependências automáticas entre modelos, testes de qualidade e documentação "
            "gerada do próprio código. É o padrão de mercado para a camada T do ELT."
        )
    )
    story.append(sp(4))
    cmp = [
        ["❌ Sem dbt", "✅ Com dbt"],
        [
            "SQL em arquivos numerados sem ordem definida",
            "Ordem automática via grafo de dependências (DAG)",
        ],
        [
            "CREATE TABLE IF NOT EXISTS na mão",
            "Materialização automática (view, table, incremental)",
        ],
        ["Zero testes de dados", "Testes declarativos em YAML (unique, not_null...)"],
        [
            "Documentação desatualizada em wiki",
            "Docs gerados do código, sempre sincronizados",
        ],
        [
            "'Quem usa essa tabela?' — ninguém sabe",
            "Lineage graph mostra impacto de cada mudança",
        ],
    ]
    story.append(ctable(cmp, [(W - 4 * cm) * 0.44, (W - 4 * cm) * 0.56]))
    story.append(sp(8))

    story.append(h2("2.2 A arquitetura de 3 camadas"))
    layers = [
        ["Camada", "Pasta", "Materialização", "Responsabilidade única"],
        [
            "Staging",
            "models/staging/bbr/",
            "VIEW",
            "Limpeza: tipos, nomes, filtros. Sem lógica de negócio.",
        ],
        [
            "Intermediate",
            "models/intermediate/",
            "VIEW",
            "Regras de negócio reutilizáveis (ex: dedup jogadores).",
        ],
        [
            "Marts",
            "models/marts/",
            "TABLE",
            "Modelo dimensional final para analistas e dashboards.",
        ],
    ]
    story.append(ctable(layers, [2.5 * cm, 4.5 * cm, 3 * cm, 7 * cm]))
    story.append(sp(6))
    story.append(
        callout(
            "💡 <b>Princípio fundamental:</b> se o Basketball Reference mudar a estrutura de uma página, "
            "APENAS a staging precisa mudar. Intermediate e marts confiam nos contratos da staging "
            "(nomes e tipos estáveis). Uma mudança na fonte não quebra 5 modelos ao mesmo tempo."
        )
    )
    story.append(sp(8))

    story.append(h2("2.3 Convenção de nomenclatura dos modelos"))
    nomes = [
        ["Padrão", "Exemplo", "Camada"],
        ["stg_[fonte]__[entidade]", "stg_bbr__player_stats", "Staging"],
        ["int_[domínio]__[propósito]", "int_players__deduped", "Intermediate"],
        ["dim_[entidade]", "dim_player", "Marts — dimensão"],
        ["fct_[processo]", "fct_player_season_stats", "Marts — fato"],
    ]
    story.append(ctable(nomes, [5 * cm, 5.5 * cm, 6 * cm]))
    story.append(sp(6))
    story.append(
        p(
            "O duplo underscore (__) separa fonte de entidade — convenção oficial dbt. "
            "Quando há múltiplas fontes (BBR, Sportradar, ESPN), fica imediatamente claro de onde "
            "cada modelo lê seus dados."
        )
    )
    story.append(sp(8))

    story.append(h2("2.4 O problema do jogador trocado — regra de negócio real"))
    story.append(
        p(
            "Quando um jogador muda de time, o BBR insere múltiplas linhas: uma por time e uma "
            "agregada (2TM, 3TM...). Sem tratamento, um jogador de 3 times aparece 4 vezes — "
            "somando jogos daria 220 numa temporada de 82."
        )
    )
    story.append(sp(4))
    story.append(
        code(
            "-- int_players__deduped.sql\n"
            "traded_players as (\n"
            "    select distinct player_name from players\n"
            "    where team_abbr = 'TOT'          -- formato legado BBR\n"
            "       or team_abbr ~ '^\\d+TM$'     -- formato atual: 2TM, 3TM...\n"
            "),\n"
            "deduped as (\n"
            "    select p.* from players p\n"
            "    left join traded_players t using (player_name)\n"
            "    where t.player_name is null       -- não foi trocado: mantém\n"
            "       or p.team_abbr ~ '^\\d+TM$'   -- foi trocado: só o agregado\n"
            ")"
        )
    )
    story.append(sp(4))
    story.append(
        tip(
            "✅ <b>Descoberto pelos testes:</b> após a correção, os testes de unicidade confirmaram "
            "que int_players__deduped e int_player_stats__season_totals têm exatamente uma linha "
            "por jogador. Sem testes, o bug teria passado silenciosamente."
        )
    )
    story.append(PageBreak())

    story.append(h2("2.5 Modelo dimensional (Star Schema)"))
    story.append(
        p(
            "Os marts implementam o Star Schema de Ralph Kimball: uma tabela fato central "
            "com métricas numéricas, conectada a tabelas dimensão com atributos descritivos."
        )
    )
    story.append(sp(4))
    star = [
        ["Tabela", "Tipo", "Grain / Conteúdo", "Surrogate Key"],
        [
            "dim_player",
            "dim",
            "1 linha por jogador ativo na temporada",
            "MD5(player_name)",
        ],
        [
            "dim_team",
            "dim",
            "1 linha por franquia ativa (30 times)",
            "MD5(abbreviation)",
        ],
        [
            "fct_player_season_stats",
            "fct",
            "1 linha por jogador por temporada (grain)",
            "MD5(player+season)",
        ],
    ]
    story.append(ctable(star, [4.5 * cm, 1.5 * cm, 7.5 * cm, 4 * cm]))
    story.append(sp(6))
    story.append(
        callout(
            "💡 <b>Surrogate keys com MD5:</b> chaves artificiais geradas pela macro "
            "generate_surrogate_key(). Mais estáveis que nomes naturais (que podem mudar de grafia) "
            "e compatíveis com joins entre sistemas que não compartilham sequências de ID."
        )
    )
    story.append(PageBreak())

    # ── PARTE 3: DOCKER ───────────────────────────────────────────────────────
    story += section("PARTE 3 — Docker Compose: Ambiente Reproduzível")

    story.append(h2("3.1 Por que Docker é fundamental para portfólio"))
    story.append(
        p(
            "Sem Docker, o projeto funciona apenas na sua máquina, com o PostgreSQL que você instalou "
            "manualmente, na porta que você configurou. Um recrutador que quiser rodar o projeto "
            "precisa de um tutorial de 20 passos antes de ver qualquer dado."
        )
    )
    story.append(
        p(
            "Com Docker Compose, qualquer pessoa executa dois comandos e tem tudo funcionando:"
        )
    )
    story.append(
        code(
            "docker compose up -d    # sobe o PostgreSQL em background\n"
            "source .venv/bin/activate\n"
            "dbt seed --profiles-dir .dbt && dbt run --profiles-dir .dbt && dbt test --profiles-dir .dbt"
        )
    )
    story.append(sp(6))

    story.append(h2("3.2 docker-compose.yml — o que cada parte faz"))
    story.append(
        code(
            "services:\n"
            "  postgres:\n"
            "    image: postgres:17-alpine         # imagem oficial, versão Alpine (menor)\n"
            "    container_name: nba_postgres\n"
            "    restart: unless-stopped           # reinicia automaticamente se o Docker reiniciar\n"
            "    environment:\n"
            "      POSTGRES_DB:       ${DBT_DBNAME:-nba}        # lê do .env ou usa 'nba'\n"
            "      POSTGRES_USER:     ${DBT_USER:-postgres}\n"
            "      POSTGRES_PASSWORD: ${DBT_PASSWORD:-postgres}\n"
            "    ports:\n"
            "      - '${DBT_PORT:-5432}:5432'      # expõe para o host\n"
            "    volumes:\n"
            "      - postgres_data:/var/lib/postgresql/data  # dados persistem entre restarts\n"
            "    healthcheck:\n"
            "      test: pg_isready -U postgres    # GitHub Actions espera este check passar"
        )
    )
    story.append(sp(6))

    story.append(h2("3.3 A variável ${VAR:-default} — Docker Compose + dbt integrados"))
    story.append(
        p(
            "As mesmas variáveis de ambiente do .env alimentam tanto o Docker Compose "
            "(que cria o banco com aquelas credenciais) quanto o dbt (que conecta usando env_var()). "
            "Não há duplicação de configuração — um único .env controla tudo."
        )
    )
    story.append(sp(4))
    story.append(
        tip(
            "✅ <b>Integração perfeita:</b> Docker cria o banco com DBT_PASSWORD=postgres, "
            "dbt lê DBT_PASSWORD=postgres para conectar. Mudar a senha exige alterar apenas o .env."
        )
    )
    story.append(sp(6))

    story.append(
        iq(
            "Como você garante que o ambiente de desenvolvimento é igual ao de produção?"
        )
    )
    story.append(
        ia(
            "Com Docker Compose, o PostgreSQL roda na mesma versão (17-alpine) em qualquer ambiente — "
            "dev local, CI no GitHub Actions e produção. As credenciais vêm de variáveis de ambiente "
            "(.env local, secrets no GitHub, variáveis de servidor em prod). O único diferencial é "
            "que em produção o volume de dados seria maior e usaria um servidor PostgreSQL gerenciado "
            "(RDS, CloudSQL) em vez de container, mas a interface é idêntica."
        )
    )
    story.append(PageBreak())

    # ── PARTE 4: DAGSTER ──────────────────────────────────────────────────────
    story += section("PARTE 4 — Dagster: Orquestração Moderna")

    story.append(h2("4.1 Dagster vs Airflow — a diferença de paradigma"))
    story.append(
        p(
            "Airflow foi criado em 2014 e pensa em <b>tasks</b>: você define o que executar e em que "
            "ordem. Dagster (2018) pensa em <b>assets</b>: você define quais <i>dados devem existir</i> "
            "e ele descobre o que rodar para produzi-los."
        )
    )
    story.append(sp(4))
    dag_vs = [
        ["", "Airflow", "Dagster"],
        ["Conceito central", "Task / DAG", "Asset (dado que deve existir)"],
        [
            "Integração com dbt",
            "BashOperator manual",
            "dbt_assets — lê o projeto dbt nativamente",
        ],
        [
            "Observabilidade",
            "Logs de task",
            "Histórico por asset, materializações, metadados",
        ],
        ["UI", "Grafo de tasks (técnico)", "Grafo de assets (intuitivo para negócio)"],
        [
            "Re-execução parcial",
            "Re-roda tasks manualmente",
            "Materializa só os assets desatualizados",
        ],
        [
            "Curva de aprendizado",
            "Alta (conceitos de XCom, DAG, hook)",
            "Média (assets são intuitivos)",
        ],
    ]
    story.append(ctable(dag_vs, [3.5 * cm, 5.5 * cm, 7.5 * cm]))
    story.append(sp(8))

    story.append(h2("4.2 Como o Dagster lê o projeto dbt automaticamente"))
    story.append(
        p(
            "O decorador <b>@dbt_assets</b> lê o manifest.json gerado por 'dbt compile' "
            "e cria um asset Dagster para cada modelo SQL automaticamente. O grafo de dependências "
            "do dbt (via ref()) é preservado no grafo de assets do Dagster."
        )
    )
    story.append(sp(4))
    story.append(
        code(
            "# orchestration/assets.py\n"
            "@dbt_assets(\n"
            "    manifest=dbt_project.manifest_path,   # lê models/staging, intermediate, marts\n"
            "    project=dbt_project,\n"
            "    deps=[scrape_players, scrape_stats,   # assets de scraping alimentam os seeds\n"
            "          scrape_teams, scrape_contracts],\n"
            ")\n"
            "def nba_dbt_assets(context, dbt: DbtCliResource):\n"
            "    yield from dbt.cli(['build'], context=context).stream()\n"
            "    # 'build' = seed + run + test em um único comando"
        )
    )
    story.append(sp(6))

    story.append(h2("4.3 Estrutura dos assets de scraping"))
    story.append(
        code(
            "@asset(\n"
            "    group_name='scraping',\n"
            "    description='Extrai roster de jogadores do BBR → seeds/players.csv',\n"
            "    kinds={'python', 'selenium'},\n"
            ")\n"
            "def scrape_players(context: AssetExecutionContext) -> None:\n"
            "    context.log.info('Iniciando scraping...')\n"
            "    _run_scraper('players.py')\n"
            "\n"
            "# O Dagster exibe cada asset na UI com:\n"
            "# — Status (materializado/falhou/nunca rodou)\n"
            "# — Última materialização (quando rodou pela última vez)\n"
            "# — Logs completos de execução\n"
            "# — Metadados (linhas produzidas, tempo de execução)"
        )
    )
    story.append(sp(6))

    story.append(h2("4.4 Schedule — execução automática semanal"))
    story.append(
        code(
            "# orchestration/definitions.py\n"
            "nba_weekly_schedule = ScheduleDefinition(\n"
            "    job=nba_pipeline_job,\n"
            "    cron_schedule='0 6 * * 1',   # toda segunda-feira às 06:00\n"
            "    name='nba_weekly_monday',\n"
            ")\n"
            "\n"
            "# Iniciar o Dagster:\n"
            "dbt compile --profiles-dir .dbt   # gera manifest.json (obrigatório)\n"
            "dagster dev -f orchestration/definitions.py\n"
            "# Acesse: http://localhost:3000"
        )
    )
    story.append(sp(6))

    story.append(iq("Por que você escolheu Dagster em vez de Airflow?"))
    story.append(
        ia(
            "Airflow é o padrão histórico — toda empresa legada tem. Mas Dagster oferece duas vantagens "
            "concretas para este projeto: (1) integração nativa com dbt via @dbt_assets, que importa "
            "todos os modelos SQL automaticamente sem escrever task por task; (2) o conceito de asset "
            "é mais próximo do que o negócio entende — 'dim_player está atualizado?' é mais intuitivo "
            "do que 'a task dbt_run do DAG nba_pipeline passou?'. Em projetos novos sem legacy, "
            "Dagster é a escolha que times modernos fazem."
        )
    )
    story.append(PageBreak())

    # ── PARTE 5: CI/CD ────────────────────────────────────────────────────────
    story += section("PARTE 5 — GitHub Actions: CI/CD Automático")

    story.append(h2("5.1 O que o CI faz e por que importa"))
    story.append(
        p(
            "CI (Continuous Integration) garante que toda mudança nos modelos SQL é validada "
            "automaticamente antes de entrar na branch principal. Sem CI, um modelo quebrado "
            "só é descoberto quando alguém roda o pipeline manualmente — às vezes dias depois."
        )
    )
    story.append(sp(4))
    ci_flow = [
        ["Evento", "Workflow disparado", "O que roda"],
        [
            "Pull Request",
            "dbt CI (ci.yml)",
            "compile → seed → run → test — valida a mudança",
        ],
        [
            "Push em master",
            "dbt CI + Docs",
            "CI completo + gera e publica a documentação",
        ],
        [
            "Dispatch manual",
            "Docs (docs.yml)",
            "Regenera e publica a documentação sob demanda",
        ],
    ]
    story.append(ctable(ci_flow, [3.5 * cm, 4.5 * cm, 9 * cm]))
    story.append(sp(6))

    story.append(h2("5.2 Como o GitHub Actions sobe o PostgreSQL automaticamente"))
    story.append(
        code(
            "# .github/workflows/ci.yml\n"
            "services:\n"
            "  postgres:\n"
            "    image: postgres:17-alpine\n"
            "    env:\n"
            "      POSTGRES_DB: nba\n"
            "      POSTGRES_USER: postgres\n"
            "      POSTGRES_PASSWORD: postgres\n"
            "    options: >-\n"
            "      --health-cmd 'pg_isready -U postgres'\n"
            "      --health-interval 10s\n"
            "# O GitHub Actions sobe o container antes dos steps e o derruba depois.\n"
            "# Nenhuma configuração manual — o banco aparece como 'localhost:5432'."
        )
    )
    story.append(sp(6))

    story.append(h2("5.3 dbt docs publicado no GitHub Pages (docs.yml)"))
    story.append(
        p(
            "O workflow docs.yml roda o pipeline completo, executa 'dbt docs generate' e publica "
            "os arquivos gerados (index.html, manifest.json, catalog.json) no GitHub Pages. "
            "Resultado: a documentação do projeto fica disponível em uma URL pública, "
            "sempre atualizada com o último código da branch principal."
        )
    )
    story.append(sp(4))
    story.append(
        tip(
            "✅ <b>Impacto no portfólio:</b> colocar a URL do dbt docs no README e no LinkedIn "
            "permite que qualquer recrutador ou engenheiro sênior explore o lineage graph e a "
            "documentação sem precisar instalar nada. É a demonstração mais direta de que "
            "você sabe construir pipelines documentados e testados."
        )
    )
    story.append(sp(6))

    story.append(iq("O que acontece se um modelo SQL quebrar em um Pull Request?"))
    story.append(
        ia(
            "O workflow ci.yml é disparado automaticamente. Ele roda dbt compile (valida sintaxe), "
            "dbt seed (carrega CSVs), dbt run (executa os modelos) e dbt test (roda os 26 testes). "
            "Se qualquer step falhar, o PR fica bloqueado — não pode ser mergeado até a correção. "
            "O erro aparece diretamente na interface do GitHub PR, com o log completo. "
            "Ninguém precisa rodar nada manualmente para descobrir que algo quebrou."
        )
    )
    story.append(PageBreak())

    # ── PARTE 6: ESTRUTURA COMPLETA ───────────────────────────────────────────
    story += section("PARTE 6 — Estrutura Completa de Arquivos")

    story.append(h2("6.1 Mapa do projeto"))
    story.append(
        code(
            "NBA Analytics/\n"
            "├── .github/\n"
            "│   └── workflows/\n"
            "│       ├── ci.yml          ← CI: compile+seed+run+test em cada PR\n"
            "│       └── docs.yml        ← publica dbt docs no GitHub Pages\n"
            "├── .dbt/\n"
            "│   └── profiles.yml        ← credenciais via env_var() (gitignored)\n"
            "├── models/\n"
            "│   ├── staging/bbr/        ← stg_bbr__*.sql  (4 modelos)\n"
            "│   ├── intermediate/       ← int_*__*.sql    (2 modelos de dedup)\n"
            "│   └── marts/\n"
            "│       ├── dimensions/     ← dim_player.sql, dim_team.sql\n"
            "│       └── facts/          ← fct_player_season_stats.sql\n"
            "├── seeds/                  ← CSVs scraped + team_info.csv estático\n"
            "├── macros/                 ← generate_surrogate_key.sql\n"
            "├── orchestration/\n"
            "│   ├── assets.py           ← assets Dagster (scraping + dbt)\n"
            "│   └── definitions.py      ← schedule, jobs, resources\n"
            "├── src/scraping/\n"
            "│   ├── common/             ← browser.py, parsing.py\n"
            "│   ├── players.py, stats.py, teams.py, contracts.py\n"
            "│   └── run_all.py          ← orquestrador local (sem Dagster)\n"
            "├── diagrama/               ← PDFs de documentação\n"
            "├── docker-compose.yml      ← PostgreSQL em container\n"
            "├── dbt_project.yml         ← configuração central do dbt\n"
            "├── requirements.txt        ← todas as dependências Python\n"
            "├── .env.example            ← template de variáveis de ambiente\n"
            "└── profiles.yml.example    ← template do profiles.yml"
        )
    )
    story.append(sp(8))

    story.append(h2("6.2 Schemas no PostgreSQL"))
    schemas = [
        ["Schema", "Criado por", "Tipo", "Consumido por"],
        ["analytics_raw", "dbt seed", "TABLE", "Modelos staging (via ref())"],
        ["analytics_staging", "dbt run", "VIEW", "Modelos intermediate"],
        ["analytics_intermediate", "dbt run", "VIEW", "Modelos marts"],
        ["analytics_marts", "dbt run", "TABLE", "Analistas, dashboards, Dagster UI"],
    ]
    story.append(ctable(schemas, [4.5 * cm, 3 * cm, 2 * cm, 7 * cm]))
    story.append(PageBreak())

    # ── PARTE 7: TESTES E QUALIDADE ────────────────────────────────────────────
    story += section("PARTE 7 — Qualidade de Dados")

    story.append(h2("7.1 Os 26 testes declarativos"))
    story.append(
        p(
            "Todos os testes são declarados em YAML — o dbt gera o SQL de validação automaticamente. "
            "Rodam localmente (dbt test) e no CI (GitHub Actions) a cada PR."
        )
    )
    story.append(sp(4))
    testes = [
        ["Tipo de teste", "Quantidade", "Onde está declarado", "O que valida"],
        ["unique", "8", "marts + intermediate YAML", "Chaves primárias sem duplicatas"],
        ["not_null", "12", "todas as camadas YAML", "Colunas obrigatórias preenchidas"],
        ["accepted_values", "4", "seeds + marts YAML", "conference = East ou West"],
        ["relationships", "2", "marts YAML", "FK de fct existe em dim"],
    ]
    story.append(ctable(testes, [3.5 * cm, 2.5 * cm, 5 * cm, 6.5 * cm]))
    story.append(sp(6))

    story.append(h2("7.2 Como rodar os testes"))
    story.append(
        code(
            "# Todos os testes\n"
            "dbt test --profiles-dir .dbt\n"
            "\n"
            "# Só um modelo\n"
            "dbt test --profiles-dir .dbt --select dim_player\n"
            "\n"
            "# Só um tipo de teste\n"
            "dbt test --profiles-dir .dbt --select test_type:unique"
        )
    )
    story.append(sp(6))

    story.append(iq("Como você garante qualidade de dados em produção?"))
    story.append(
        ia(
            "Tenho 26 testes declarativos no dbt cobrindo unique, not_null, accepted_values e "
            "relationships. Eles rodam automaticamente no CI (GitHub Actions) a cada PR — "
            "qualquer modelo quebrado bloqueia o merge. Em produção, o Dagster re-executa os "
            "testes após cada materialização. Para escala maior adicionaria Elementary para "
            "rastrear anomalias históricas (ex: volume de linhas caiu 20% sem motivo aparente) "
            "e testes customizados em SQL para regras de negócio mais específicas."
        )
    )
    story.append(PageBreak())

    # ── PARTE 8: GUIA DE ENTREVISTA ────────────────────────────────────────────
    story += section("PARTE 8 — Guia de Entrevista Pleno/Sênior")

    story.append(h2("8.1 O pitch de 2 minutos"))
    story.append(
        callout(
            '"Construí um pipeline de dados end-to-end para análise de estatísticas da NBA. '
            "O dado vem do Basketball Reference via scraping com Selenium — o site bloqueia "
            "requests diretos. Os CSVs são carregados no PostgreSQL via dbt seed e transformados "
            "em 3 camadas: staging para limpeza, intermediate para regras de negócio como "
            "de-duplicação de jogadores trocados, e marts com Star Schema. "
            "O ambiente roda em Docker Compose, a orquestração é feita com Dagster "
            "(assets nativos dbt, schedule semanal), e o CI/CD no GitHub Actions valida "
            "os 26 testes de qualidade em cada PR. A documentação é publicada automaticamente "
            'no GitHub Pages via dbt docs."'
        )
    )
    story.append(sp(8))

    story.append(h2("8.2 Perguntas — nível Pleno"))

    story.append(iq("Qual a diferença entre ETL e ELT?"))
    story.append(
        ia(
            "ETL transforma antes de carregar — necessário quando storage era caro. "
            "ELT carrega bruto e transforma dentro do banco — padrão moderno. "
            "dbt é fundamentalmente ELT: os dados chegam via seed sem transformação, "
            "o banco executa os SELECTs dos modelos. Vantagem: dados brutos sempre disponíveis "
            "para análises não previstas sem re-extrair da fonte."
        )
    )
    story.append(sp(4))

    story.append(iq("O que é materialização no dbt e quando usar cada tipo?"))
    story.append(
        ia(
            "VIEW: sem storage, executa na consulta — ideal para staging e intermediate. "
            "TABLE: persiste fisicamente — ideal para marts consultados por analistas. "
            "INCREMENTAL: processa só registros novos — para tabelas grandes em produção. "
            "EPHEMERAL: CTE inline, nem cria objeto no banco — para lógica auxiliar simples. "
            "No projeto: staging e intermediate são VIEW, marts são TABLE."
        )
    )
    story.append(sp(4))

    story.append(iq("O que é um DAG e como o dbt usa esse conceito?"))
    story.append(
        ia(
            "DAG (Directed Acyclic Graph) é um grafo de dependências sem ciclos. "
            "No dbt, cada ref() em um modelo cria uma aresta no grafo. O dbt calcula "
            "automaticamente a ordem de execução e paraleliza modelos sem dependência mútua. "
            "fct_player_season_stats só roda depois de dim_player e dim_team existirem, "
            "que só rodam depois dos intermediates, que dependem do staging. "
            "Nunca precisei escrever essa ordem manualmente."
        )
    )
    story.append(sp(6))

    story.append(h2("8.3 Perguntas — nível Sênior"))

    story.append(iq("Como você escalaria esse pipeline para múltiplas temporadas?"))
    story.append(
        ia(
            "Três mudanças principais: (1) coluna season em todos os seeds e modelos para identificar "
            "a temporada de cada registro; (2) materialização INCREMENTAL na fct — processa só "
            "os dados da temporada atual sem reconstruir histórico; (3) SCD Type 2 na dim_player "
            "para rastrear mudanças de time entre temporadas com effective_from/effective_to. "
            "O Dagster gerenciaria qual partição de dados está desatualizada e re-materializaria "
            "só ela."
        )
    )
    story.append(sp(4))

    story.append(iq("Como o CI garante que nenhum modelo quebrado chega em produção?"))
    story.append(
        ia(
            "O GitHub Actions ci.yml roda em cada PR: sobe PostgreSQL como service container, "
            "instala dbt, escreve o profiles.yml com as credenciais de CI, e executa "
            "compile → seed → run → test em sequência. Se qualquer step falhar, o PR fica "
            "bloqueado. Em projetos maiores usaria dbt slim CI (--state flag) para rodar "
            "apenas modelos que mudaram no PR, reduzindo tempo de 10 minutos para 1-2 minutos."
        )
    )
    story.append(sp(4))

    story.append(iq("Por que Dagster e não Airflow para orquestrar o pipeline dbt?"))
    story.append(
        ia(
            "Para este caso específico: @dbt_assets importa todos os 8 modelos dbt automaticamente "
            "a partir do manifest.json — sem escrever uma task por modelo. No Airflow eu escreveria "
            "BashOperators manuais para seed, run e test, sem granularidade por modelo. "
            "Além disso, a UI do Dagster mostra o grafo de assets com status de saúde por modelo, "
            "não apenas 'o DAG passou ou falhou'. Em ambiente com Airflow já estabelecido usaria "
            "o provider astronomer-cosmos que traz integração similar."
        )
    )
    story.append(sp(6))

    story.append(h2("8.4 Red flags para evitar"))
    red = [
        ["❌ Não diga", "✅ Diga no lugar"],
        ["'Segui um tutorial'", "'Enfrentei o problema X e resolvi assim...'"],
        ["'dbt é tipo um ORM'", "'dbt é transformador SQL com gestão de DAG e testes'"],
        [
            "'Não sei por que funciona'",
            "'A razão dessa escolha foi... (explique trade-offs)'",
        ],
        [
            "'É só um projeto pessoal simples'",
            "'Implementei padrões de produção: CI, Docker, Dagster'",
        ],
        [
            "'Nunca usei em produção'",
            "'Apliquei as práticas que usaria em prod: env_var, CI, docs'",
        ],
    ]
    story.append(ctable(red, [(W - 4 * cm) * 0.38, (W - 4 * cm) * 0.62], hbg=RED))
    story.append(PageBreak())

    # ── PARTE 9: PRÓXIMOS PASSOS ──────────────────────────────────────────────
    story += section("PARTE 9 — Próximos Passos e Glossário")

    story.append(h2("9.1 Roadmap de evolução"))
    roadmap = [
        ["Evolução", "Dificuldade", "O que demonstra"],
        [
            "Modelos incrementais + múltiplas temporadas",
            "⭐⭐⭐",
            "Modelagem temporal, eficiência em escala",
        ],
        ["SCD Type 2 em dim_player", "⭐⭐⭐", "Histórico de mudanças em dimensões"],
        [
            "Elementary (observabilidade de qualidade)",
            "⭐⭐",
            "Monitoramento contínuo de anomalias",
        ],
        [
            "Dashboard com Metabase ou Superset",
            "⭐⭐",
            "Entrega de valor visível ao usuário final",
        ],
        [
            "Testes customizados em SQL (dbt macros)",
            "⭐⭐⭐",
            "Qualidade de dados avançada",
        ],
        [
            "Migrar para Snowflake ou BigQuery",
            "⭐⭐",
            "Cloud data warehouse de mercado",
        ],
        [
            "dbt Snapshots para histórico de contratos",
            "⭐⭐",
            "Rastreamento de mudanças ao longo do tempo",
        ],
    ]
    story.append(ctable(roadmap, [7.5 * cm, 2.5 * cm, 7 * cm]))
    story.append(sp(8))

    story.append(h2("9.2 Glossário completo"))
    gloss = [
        ["Termo", "Definição"],
        [
            "Asset (Dagster)",
            "Dado que deve existir — o conceito central do Dagster (equivalente a tabela/view)",
        ],
        [
            "CI/CD",
            "Continuous Integration/Delivery — validação e publicação automatizadas a cada mudança",
        ],
        [
            "DAG",
            "Directed Acyclic Graph — grafo de dependências sem ciclos (base do dbt e Dagster)",
        ],
        [
            "ELT",
            "Extract-Load-Transform — dados brutos carregados primeiro, transformados no banco",
        ],
        ["Grain", "A granularidade da tabela fato — o que cada linha representa"],
        [
            "Jinja2",
            "Sistema de templates Python usado pelo dbt para lógica em SQL ({{ ref() }}, {% if %})",
        ],
        [
            "Lineage",
            "Mapa de dependências entre modelos — mostra de onde os dados vêm e para onde vão",
        ],
        ["Macro", "Função Jinja reutilizável no dbt (ex: generate_surrogate_key)"],
        [
            "Materialização",
            "Como o dbt persiste um modelo: view, table, incremental ou ephemeral",
        ],
        [
            "Profile",
            "Arquivo de configuração com credenciais de conexão (.dbt/profiles.yml)",
        ],
        [
            "ref()",
            "Função dbt que cria dependência entre modelos e resolve o nome completo da tabela",
        ],
        [
            "SCD Type 2",
            "Slowly Changing Dimension — técnica para rastrear histórico de mudanças em dimensões",
        ],
        [
            "Schema",
            "Namespace no PostgreSQL que agrupa tabelas (analytics_raw, analytics_marts...)",
        ],
        [
            "Seed",
            "CSV carregado no banco pelo dbt seed — usado para dados de referência ou ingestão",
        ],
        [
            "Star Schema",
            "Modelo dimensional com tabela fato central conectada a tabelas dimensão",
        ],
        [
            "Surrogate Key",
            "ID artificial gerado (MD5, UUID) — estável e independente dos dados de negócio",
        ],
    ]
    story.append(ctable(gloss, [3.5 * cm, 13 * cm]))
    story.append(sp(10))

    story.append(hr(ORANGE, 2))
    story.append(
        Paragraph(
            "NBA Analytics Portfolio — dbt Core 1.9 · PostgreSQL 17 · Dagster · Docker · GitHub Actions",
            S["footer"],
        )
    )

    return story


# ── BUILD ─────────────────────────────────────────────────────────────────────
def build_pdf():
    frame = Frame(1.5 * cm, 1.8 * cm, W - 3 * cm, H - 3.2 * cm, id="normal")
    template = PageTemplate(id="main", frames=[frame], onPage=on_page)
    doc = BaseDocTemplate(
        OUTPUT,
        pagesize=A4,
        pageTemplates=[template],
        title="NBA Analytics — Guia Completo",
        author="Henri",
        subject="Portfolio de Engenharia de Dados — Pleno/Sênior",
    )
    story = build_content()
    doc.build(story)
    size_mb = os.path.getsize(OUTPUT) / 1024 / 1024
    print(f"\n✅ PDF gerado: {OUTPUT}")
    print(f"   Tamanho: {size_mb:.2f} MB")


if __name__ == "__main__":
    build_pdf()
