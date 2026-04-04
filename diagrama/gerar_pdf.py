"""
Gerador do PDF explicativo do projeto NBA Analytics.
Execução: python diagrama/gerar_pdf.py
Saída:    diagrama/NBA_Analytics_Guia_Completo.pdf
"""

import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
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
    KeepTogether,
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

# ── Paleta de cores ──────────────────────────────────────────────────────────
ORANGE = colors.HexColor("#FF6B35")  # dbt brand
DARK = colors.HexColor("#1A1A2E")
BLUE = colors.HexColor("#16213E")
LIGHT_BG = colors.HexColor("#F8F9FA")
GRAY = colors.HexColor("#6C757D")
GREEN = colors.HexColor("#28A745")
RED = colors.HexColor("#DC3545")
YELLOW = colors.HexColor("#FFC107")
TEAL = colors.HexColor("#17A2B8")

OUTPUT = os.path.join(os.path.dirname(__file__), "NBA_Analytics_Guia_Completo.pdf")
W, H = A4


# ── Estilos ──────────────────────────────────────────────────────────────────
base_styles = getSampleStyleSheet()


def make_styles():
    s = {}

    s["capa_titulo"] = ParagraphStyle(
        "capa_titulo",
        fontSize=32,
        textColor=colors.white,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    s["capa_sub"] = ParagraphStyle(
        "capa_sub",
        fontSize=16,
        textColor=ORANGE,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    s["capa_desc"] = ParagraphStyle(
        "capa_desc",
        fontSize=11,
        textColor=colors.HexColor("#CCCCCC"),
        fontName="Helvetica",
        alignment=TA_CENTER,
        spaceAfter=2,
    )

    s["h1"] = ParagraphStyle(
        "h1",
        fontSize=20,
        textColor=DARK,
        fontName="Helvetica-Bold",
        spaceBefore=24,
        spaceAfter=8,
        borderPad=4,
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
        bulletIndent=4,
        alignment=TA_LEFT,
    )
    s["sub_bullet"] = ParagraphStyle(
        "sub_bullet",
        fontSize=9.5,
        textColor=DARK,
        fontName="Helvetica",
        leading=14,
        spaceAfter=2,
        leftIndent=32,
        bulletIndent=20,
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
    s["interview"] = ParagraphStyle(
        "interview",
        fontSize=10,
        textColor=colors.HexColor("#155724"),
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
    s["label_orange"] = ParagraphStyle(
        "label_orange",
        fontSize=9,
        textColor=colors.white,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
        backColor=ORANGE,
        borderPad=3,
    )
    s["label_blue"] = ParagraphStyle(
        "label_blue",
        fontSize=9,
        textColor=colors.white,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
        backColor=BLUE,
        borderPad=3,
    )
    return s


S = make_styles()


# ── Helpers ──────────────────────────────────────────────────────────────────
def hr(color=ORANGE, thickness=1.5):
    return HRFlowable(width="100%", thickness=thickness, color=color, spaceAfter=6)


def sp(n=6):
    return Spacer(1, n)


def h1(text):
    return Paragraph(text, S["h1"])


def h2(text):
    return Paragraph(text, S["h2"])


def h3(text):
    return Paragraph(text, S["h3"])


def p(text):
    return Paragraph(text, S["body"])


def b(text):
    return Paragraph(f"• {text}", S["bullet"])


def bb(text):
    return Paragraph(f"– {text}", S["sub_bullet"])


def code(text):
    return Paragraph(
        text.replace("\n", "<br/>").replace("  ", "&nbsp;&nbsp;"), S["code"]
    )


def callout(text):
    return Paragraph(text, S["callout"])


def interview_q(text):
    return Paragraph(f"🎯 Pergunta de entrevista: {text}", S["interview"])


def interview_a(text):
    return Paragraph(text, S["interview_ans"])


def section_divider(title):
    return [
        sp(12),
        hr(ORANGE, 2),
        Paragraph(title, S["h1"]),
        hr(ORANGE, 0.5),
        sp(4),
    ]


def colored_table(
    data,
    col_widths,
    header_bg=DARK,
    header_fg=colors.white,
    row_bg=LIGHT_BG,
    alt_bg=colors.white,
):
    style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), header_bg),
            ("TEXTCOLOR", (0, 0), (-1, 0), header_fg),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [row_bg, alt_bg]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDDDDD")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]
    )
    return Table(data, colWidths=col_widths, style=style, hAlign="LEFT")


# ── Página de cabeçalho/rodapé ───────────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    # Rodapé
    canvas.setFillColor(DARK)
    canvas.rect(0, 0, W, 1.2 * cm, fill=1, stroke=0)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.white)
    canvas.drawString(
        1.5 * cm, 0.45 * cm, "NBA Analytics — Guia Completo dbt + PostgreSQL"
    )
    canvas.drawRightString(W - 1.5 * cm, 0.45 * cm, f"Página {doc.page}")
    canvas.restoreState()


# ── CONTEÚDO ─────────────────────────────────────────────────────────────────
def build_content():
    story = []

    # ════════════════════════════════════════════════════════════════════════
    # CAPA
    # ════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 3 * cm))

    # Bloco de cabeçalho colorido
    capa_data = [
        [
            Paragraph(
                "<br/><b>NBA ANALYTICS</b><br/>"
                "<font size=14 color='#FF6B35'>Pipeline de Engenharia de Dados</font><br/>"
                "<font size=10 color='#AAAAAA'>dbt Core · PostgreSQL · Python · Selenium</font><br/><br/>",
                ParagraphStyle(
                    "ct",
                    fontSize=28,
                    textColor=colors.white,
                    fontName="Helvetica-Bold",
                    alignment=TA_CENTER,
                ),
            )
        ]
    ]
    capa_t = Table(capa_data, colWidths=[W - 4 * cm])
    capa_t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), DARK),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 24),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 24),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    story.append(capa_t)
    story.append(sp(20))

    desc_data = [
        [
            Paragraph(
                "📖 O QUE VOCÊ VAI APRENDER",
                ParagraphStyle(
                    "x",
                    fontSize=11,
                    textColor=DARK,
                    fontName="Helvetica-Bold",
                    alignment=TA_CENTER,
                    spaceAfter=8,
                ),
            ),
        ]
    ]
    story.append(Table(desc_data, colWidths=[W - 4 * cm]))
    story.append(sp(8))

    itens_capa = [
        ["🔧 O que é dbt e por que ele existe", "📁 Cada pasta e arquivo do projeto"],
        ["📊 Como funciona o pipeline completo", "🧠 Regras de negócio implementadas"],
        [
            "🏗️ Arquitetura de 3 camadas (staging/int/marts)",
            "🧪 Testes de qualidade de dados",
        ],
        [
            "🐍 Os scrapers Python (Selenium + BBR)",
            "💼 Como falar sobre tudo isso em entrevista",
        ],
    ]
    capa_grid = Table(itens_capa, colWidths=[(W - 4 * cm) / 2] * 2)
    capa_grid.setStyle(
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
    story.append(capa_grid)
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PARTE 1 — O QUE É DBT
    # ════════════════════════════════════════════════════════════════════════
    story += section_divider("PARTE 1 — O Que é dbt e Por Que Usamos")

    story.append(h2("1.1 A Definição Simples"))
    story.append(
        p(
            "<b>dbt</b> significa <b>data build tool</b>. É uma ferramenta open-source que permite "
            "escrever transformações de dados em SQL puro, mas com superpoderes: dependências automáticas "
            "entre modelos, testes de qualidade, documentação gerada automaticamente e controle de versão."
        )
    )
    story.append(
        p(
            "Pense no dbt como o equivalente do <b>Git + Make + pytest</b> para SQL. Você escreve SELECT, "
            "o dbt cuida do CREATE TABLE/VIEW, da ordem certa de execução e dos testes."
        )
    )
    story.append(sp(8))

    story.append(h2("1.2 O Problema Que o dbt Resolve"))
    story.append(
        p(
            "Antes do dbt, pipelines de dados em empresas eram caóticos: scripts SQL espalhados em pastas, "
            "sem saber qual rodava antes de qual, sem testes, e documentação inexistente ou desatualizada. "
            "Um analista quebrava um pipeline sem perceber porque não sabia que aquela tabela era usada em outros 5 lugares."
        )
    )
    story.append(sp(4))

    sem_dbt_com_dbt = [
        ["❌ Sem dbt", "✅ Com dbt"],
        [
            "SQL em arquivos .sql sem ordem definida",
            "Ordem automática via grafo de dependências (DAG)",
        ],
        [
            "CREATE TABLE IF NOT EXISTS na mão",
            "dbt materializa como TABLE ou VIEW automaticamente",
        ],
        [
            "Zero testes de dados",
            "Testes declarativos: unique, not_null, relationships",
        ],
        [
            "Documentação em planilhas desatualizadas",
            "Documentação gerada do próprio código YAML",
        ],
        [
            "'Quem usa essa tabela?' — ninguém sabe",
            "Lineage graph mostra o impacto de cada mudança",
        ],
        ["Deploy manual e arriscado", "dbt run executa só o que mudou, na ordem certa"],
    ]
    story.append(
        colored_table(sem_dbt_com_dbt, [(W - 4 * cm) * 0.45, (W - 4 * cm) * 0.55])
    )
    story.append(sp(8))

    story.append(h2("1.3 Como o dbt Funciona (o ciclo de vida)"))
    story.append(
        p(
            "O dbt opera em cima de um banco de dados já existente — no nosso caso, PostgreSQL. "
            "Ele <b>não move dados</b>, ele <b>transforma dados que já estão no banco</b>. "
            "O fluxo é:"
        )
    )
    story.append(b("Você escreve um arquivo <b>.sql</b> com um SELECT"))
    story.append(
        b(
            "O dbt compila esse SELECT e gera o SQL final com os nomes de tabela corretos"
        )
    )
    story.append(
        b(
            "O dbt executa no PostgreSQL, criando TABLE ou VIEW dependendo da configuração"
        )
    )
    story.append(
        b("O dbt registra o resultado no seu metadata e oferece docs e testes")
    )
    story.append(sp(6))

    story.append(
        callout(
            "💡 <b>Analogia para entrevista:</b> dbt está para SQL assim como React está para JavaScript — "
            "você não escreve HTML na mão, você descreve o que quer e o framework gera o código otimizado. "
            "dbt não é um orquestrador (não é o Airflow), é um transformador."
        )
    )
    story.append(sp(8))

    story.append(h2("1.4 dbt Core vs dbt Cloud"))
    story.append(
        p(
            "Existem dois produtos: <b>dbt Core</b> (open-source, linha de comando, gratuito) e "
            "<b>dbt Cloud</b> (SaaS, interface web, agendamento, CI/CD integrado, pago). "
            "Neste projeto usamos <b>dbt Core 1.9.10</b> — a versão de linha de comando, "
            "que é o que você controla 100% e que aparece em entrevistas técnicas."
        )
    )
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PARTE 2 — ARQUITETURA DO PROJETO
    # ════════════════════════════════════════════════════════════════════════
    story += section_divider("PARTE 2 — Arquitetura do Projeto")

    story.append(h2("2.1 Visão Geral do Pipeline"))
    story.append(
        p(
            "O projeto segue o padrão <b>ELT</b> (Extract → Load → Transform), "
            "não ETL. A diferença é importante:"
        )
    )
    story.append(
        b(
            "<b>ETL</b> — transforma os dados ANTES de carregar no banco. Mais antigo, menos flexível."
        )
    )
    story.append(
        b(
            "<b>ELT</b> — carrega os dados RAW primeiro, transforma DENTRO do banco. Padrão moderno (dbt é ELT)."
        )
    )
    story.append(sp(8))

    pipeline = [
        ["Etapa", "Ferramenta", "O que acontece", "Saída"],
        [
            "Extract",
            "Python + Selenium",
            "Scraping do Basketball Reference",
            "Arquivos CSV",
        ],
        [
            "Load",
            "dbt seed",
            "Carrega os CSVs no PostgreSQL (schema raw)",
            "Tabelas raw",
        ],
        [
            "Transform 1",
            "dbt staging",
            "Limpa tipos, renomeia colunas",
            "Views staging",
        ],
        [
            "Transform 2",
            "dbt intermediate",
            "Regras de negócio (dedup jogadores)",
            "Views intermediate",
        ],
        [
            "Transform 3",
            "dbt marts",
            "Modelo dimensional (dim_*, fct_*)",
            "Tables marts",
        ],
    ]
    story.append(colored_table(pipeline, [2.8 * cm, 3.2 * cm, 6.5 * cm, 4 * cm]))
    story.append(sp(10))

    story.append(h2("2.2 A Separação em Schemas do PostgreSQL"))
    story.append(
        p(
            "O dbt cria schemas diferentes no PostgreSQL para cada camada. "
            "Isso é feito com a configuração <b>+schema</b> no dbt_project.yml. "
            "O prefixo <b>analytics_</b> é o schema padrão do profile + o sufixo configurado."
        )
    )
    story.append(sp(4))

    schemas = [
        ["Schema no PostgreSQL", "Camada dbt", "Tipo de objeto", "Quem usa"],
        ["analytics_raw", "seeds", "TABLE", "Só o dbt (não exponha para analistas)"],
        ["analytics_staging", "staging", "VIEW", "Engenheiros de dados, para debug"],
        [
            "analytics_intermediate",
            "intermediate",
            "VIEW",
            "Engenheiros de dados, para debug",
        ],
        ["analytics_marts", "marts", "TABLE", "Analistas, dashboards, notebooks"],
    ]
    story.append(colored_table(schemas, [4 * cm, 3.5 * cm, 2.5 * cm, 6.5 * cm]))
    story.append(sp(8))

    story.append(
        callout(
            "💡 <b>Por que VIEW para staging/intermediate e TABLE para marts?</b><br/>"
            "VIEWs não ocupam espaço em disco — elas executam a query na hora que você consulta. "
            "Para camadas intermediárias que mudam todo dia, isso é ótimo. "
            "TABLEs persistem os dados e são mais rápidas para consultas analíticas dos usuários finais. "
            "Marts são consultados por analistas que não devem esperar a query rodar do zero toda vez."
        )
    )
    story.append(PageBreak())

    story.append(h2("2.3 O DAG — Grafo de Dependências"))
    story.append(
        p(
            "O coração do dbt é o <b>DAG (Directed Acyclic Graph)</b>. "
            "Quando você usa <b>{{ ref('nome_modelo') }}</b> dentro de um arquivo SQL, "
            "o dbt entende que aquele modelo depende do outro e garante a ordem correta de execução. "
            "Nunca vai tentar criar fct_player_season_stats antes de dim_player estar pronta."
        )
    )
    story.append(sp(6))

    dag_data = [
        [
            "seeds/players.csv\nseeds/players_stats.csv\nseeds/team.csv\nseeds/team_info.csv",
            "→",
            "stg_bbr__players\nstg_bbr__player_stats\nstg_bbr__teams",
            "→",
            "int_players__deduped\nint_player_stats__season_totals",
            "→",
            "dim_player\ndim_team\nfct_player_season_stats",
        ],
    ]
    dag_t = Table(
        dag_data,
        colWidths=[
            3.5 * cm,
            0.6 * cm,
            4.2 * cm,
            0.6 * cm,
            4.2 * cm,
            0.6 * cm,
            4.2 * cm,
        ],
    )
    dag_t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Courier"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#6C757D")),
                ("BACKGROUND", (2, 0), (2, 0), TEAL),
                ("BACKGROUND", (4, 0), (4, 0), BLUE),
                ("BACKGROUND", (6, 0), (6, 0), ORANGE),
                ("TEXTCOLOR", (0, 0), (0, 0), colors.white),
                ("TEXTCOLOR", (2, 0), (2, 0), colors.white),
                ("TEXTCOLOR", (4, 0), (4, 0), colors.white),
                ("TEXTCOLOR", (6, 0), (6, 0), colors.white),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("FONTSIZE", (1, 0), (1, 0), 14),
                ("FONTSIZE", (3, 0), (3, 0), 14),
                ("FONTSIZE", (5, 0), (5, 0), 14),
            ]
        )
    )
    story.append(dag_t)
    story.append(Paragraph("raw → staging → intermediate → marts", S["caption"]))
    story.append(sp(8))

    story.append(interview_q("O que é um DAG no contexto de pipelines de dados?"))
    story.append(
        interview_a(
            "DAG é um Grafo Acíclico Dirigido — uma estrutura onde cada nó é uma tarefa e "
            "as arestas representam dependências. 'Acíclico' significa que não há loops: "
            "A depende de B, B depende de C, mas C não pode depender de A. "
            "No dbt, o DAG é construído automaticamente a partir das funções ref() nos modelos SQL. "
            "Isso garante ordem de execução correta e permite paralelizar modelos independentes."
        )
    )
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PARTE 3 — CADA ARQUIVO E PASTA EXPLICADO
    # ════════════════════════════════════════════════════════════════════════
    story += section_divider("PARTE 3 — Cada Arquivo e Pasta Explicado")

    # dbt_project.yml
    story.append(h2("3.1 dbt_project.yml — O Arquivo de Configuração Central"))
    story.append(
        p(
            "É o arquivo que diz ao dbt <i>quem você é</i>. Fica na raiz do projeto e define: "
            "nome do projeto, qual profile usar, onde ficam os modelos/seeds/macros, "
            "e configurações globais de materialização e schema."
        )
    )
    story.append(sp(4))
    story.append(
        code(
            "name: nba_analytics          # nome do projeto\n"
            "profile: nba_analytics       # aponta para .dbt/profiles.yml\n"
            "\n"
            'seed-paths:  ["seeds"]        # onde ficam os CSVs\n'
            'model-paths: ["models"]       # onde ficam os .sql\n'
            'macro-paths: ["macros"]       # onde ficam as macros Jinja\n'
            "\n"
            "seeds:\n"
            "  nba_analytics:\n"
            "    +schema: raw              # seeds vão para schema analytics_raw\n"
            "    +quote_columns: true      # preserva maiúsculas nos nomes de colunas\n"
            "\n"
            "models:\n"
            "  nba_analytics:\n"
            "    staging:\n"
            "      +materialized: view     # staging = VIEW (sem custo de armazenamento)\n"
            "      +schema: staging        # analytics_staging\n"
            "    intermediate:\n"
            "      +materialized: view\n"
            "      +schema: intermediate\n"
            "    marts:\n"
            "      +materialized: table    # marts = TABLE (rápido para analistas)\n"
            "      +schema: marts"
        )
    )
    story.append(sp(6))
    story.append(
        callout(
            "⚠️ <b>quote_columns: true</b> — Basketball Reference usa colunas como "
            "Player, Team com letra maiúscula. No PostgreSQL, nomes sem aspas são "
            "convertidos para minúsculo. quote_columns: true força o dbt a criar a coluna "
            'como "Player" (com aspas) preservando o case original.'
        )
    )
    story.append(sp(8))

    # profiles.yml
    story.append(h2("3.2 .dbt/profiles.yml — Credenciais de Conexão"))
    story.append(
        p(
            "O profiles.yml diz ao dbt <i>como conectar ao banco de dados</i>. "
            "É o arquivo mais sensível do projeto — nunca deve ir para o Git com credenciais reais. "
            "Por isso está no .gitignore e usamos <b>env_var()</b> para ler do ambiente."
        )
    )
    story.append(sp(4))
    story.append(
        code(
            "nba_analytics:               # mesmo nome que 'profile' no dbt_project.yml\n"
            "  target: dev\n"
            "  outputs:\n"
            "    dev:\n"
            "      type: postgres\n"
            "      host: \"{{ env_var('DBT_HOST', 'localhost') }}\"\n"
            "      port: \"{{ env_var('DBT_PORT', '5432') | int }}\"\n"
            "      dbname: \"{{ env_var('DBT_DBNAME', 'nba') }}\"\n"
            "      user: \"{{ env_var('DBT_USER', 'postgres') }}\"\n"
            "      password: \"{{ env_var('DBT_PASSWORD', 'postgres') }}\"\n"
            "      schema: analytics       # schema padrão (prefixo para outros schemas)\n"
            "      threads: 4              # quantos modelos rodam em paralelo"
        )
    )
    story.append(sp(6))
    story.append(
        p(
            "A sintaxe <b>{{ env_var('DBT_HOST', 'localhost') }}</b> é <b>Jinja2</b>, "
            "o sistema de template que o dbt usa. Ela lê a variável de ambiente DBT_HOST; "
            "se não existir, usa 'localhost' como fallback. Isso permite que em produção "
            "você defina as variáveis de ambiente sem tocar no código."
        )
    )
    story.append(PageBreak())

    # seeds/
    story.append(h2("3.3 seeds/ — A Camada Raw (Dados Brutos)"))
    story.append(
        p(
            "Seeds são arquivos CSV que o dbt carrega no banco com <b>dbt seed</b>. "
            "Eles representam a camada mais crua dos dados — exatamente como vieram da fonte, "
            "sem transformação. No nosso caso, são os arquivos gerados pelos scrapers Python."
        )
    )
    story.append(sp(4))

    seeds_table = [
        ["Arquivo", "Origem", "Linhas (aprox.)", "Schema carregado"],
        ["players.csv", "BBR per-game page (roster)", "735", "analytics_raw.players"],
        [
            "players_stats.csv",
            "BBR per-game page (stats)",
            "735",
            "analytics_raw.players_stats",
        ],
        ["team.csv", "BBR teams page", "87", "analytics_raw.team"],
        ["team_info.csv", "Estático (mantido à mão)", "30", "analytics_raw.team_info"],
    ]
    story.append(colored_table(seeds_table, [3.5 * cm, 5.5 * cm, 2.5 * cm, 5 * cm]))
    story.append(sp(6))

    story.append(b("<b>Por que usar dbt seed em vez de carregar direto no banco?</b>"))
    story.append(
        bb(
            "O seed entra no DAG do dbt — os modelos que dependem dele sabem que precisam esperar o seed terminar"
        )
    )
    story.append(bb("O schema.yml do seed documenta e testa os dados da camada raw"))
    story.append(bb("Se o CSV mudar, dbt seed recria a tabela automaticamente"))
    story.append(sp(6))

    story.append(
        p(
            "<b>seeds/schema.yml</b> — Documento os seeds com descrições e testes de qualidade. "
            "Note que os testes de not_null ficam no staging (não no seed) por um motivo técnico: "
            'o PostgreSQL com quote_columns cria a coluna como <b>"Player"</b> (case-sensitive) '
            "mas o dbt gera o teste SQL como <b>Player</b> (sem aspas, vai para lowercase). "
            "Os testes ficam na camada seguinte onde os nomes já foram normalizados."
        )
    )
    story.append(sp(8))

    story.append(h2("3.4 macros/ — Funções Reutilizáveis em Jinja"))
    story.append(
        p(
            "Macros são funções Jinja2 que você pode chamar de qualquer modelo dbt. "
            "São o equivalente de funções Python no mundo dbt — evitam repetição de lógica."
        )
    )
    story.append(sp(4))

    story.append(h3("macros/generate_surrogate_key.sql"))
    story.append(
        p(
            "Gera uma <b>chave substituta (surrogate key)</b> usando MD5 de uma lista de colunas. "
            "Uma chave substituta é um ID artificial que não depende dos dados reais — "
            "é mais estável que usar o nome do jogador diretamente como chave primária."
        )
    )
    story.append(sp(4))
    story.append(
        code(
            "{% macro generate_surrogate_key(field_list) %}\n"
            "  md5(\n"
            "    {%- for field in field_list %}\n"
            "      coalesce(cast({{ field }} as text), '__NULL__')\n"
            "      {%- if not loop.last %} || '|' || {% endif %}\n"
            "    {%- endfor %}\n"
            "  )\n"
            "{% endmacro %}"
        )
    )
    story.append(sp(4))
    story.append(
        p(
            "Uso: <b>{{ generate_surrogate_key(['player_name']) }}</b> → gera MD5('LeBron James') → "
            "um hash de 32 caracteres que identifica o jogador de forma única. "
            "Se o mesmo jogador aparecer em datasets de temporadas diferentes, "
            "a chave continua estável porque é derivada do nome."
        )
    )
    story.append(sp(6))

    story.append(
        callout(
            "💡 <b>Por que não usar o nome do jogador diretamente como PK?</b><br/>"
            "Porque nomes mudam (correção de grafia, nomes artísticos), e joins com strings "
            "são mais lentos do que joins com hashes de tamanho fixo. "
            "Em produção com milhões de registros, isso faz diferença mensurável."
        )
    )
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PARTE 4 — STAGING LAYER
    # ════════════════════════════════════════════════════════════════════════
    story += section_divider("PARTE 4 — Staging Layer (Camada de Limpeza)")

    story.append(h2("4.1 O Que É e Por Que Existe"))
    story.append(
        p(
            "A staging layer tem <b>uma única responsabilidade</b>: pegar os dados brutos do seed "
            "e limpá-los — sem lógica de negócio, sem joins entre fontes diferentes, sem cálculos. "
            "Apenas: renomear colunas, corrigir tipos de dados, filtrar linhas inválidas."
        )
    )
    story.append(sp(4))
    story.append(
        p(
            "O princípio fundamental é: <b>se a fonte mudar, só a staging precisa mudar</b>. "
            "Todos os modelos downstream confiam nos contratos da staging — nomes de colunas "
            "e tipos de dados estáveis."
        )
    )
    story.append(sp(6))

    story.append(h2("4.2 Convenção de Nomenclatura: stg_bbr__entidade.sql"))
    story.append(
        p("O nome dos arquivos segue a convenção: <b>stg_[fonte]__[entidade].sql</b>")
    )
    story.append(b("<b>stg</b> = staging layer"))
    story.append(b("<b>bbr</b> = Basketball Reference (a fonte dos dados)"))
    story.append(
        b(
            "<b>__</b> (dois underscores) = separador fonte/entidade (convenção dbt oficial)"
        )
    )
    story.append(b("<b>players, player_stats, teams</b> = a entidade/domínio"))
    story.append(sp(4))
    story.append(
        p(
            "Essa convenção é importante porque quando você tem múltiplas fontes "
            "(ex: stg_salesforce__accounts, stg_stripe__payments), "
            "fica imediatamente claro de onde cada dado veio."
        )
    )
    story.append(sp(6))

    story.append(h2("4.3 stg_bbr__players.sql — Análise Linha a Linha"))
    story.append(sp(4))
    story.append(
        code(
            "with source as (\n"
            "    select * from {{ ref('players') }}  -- ref() = depende do seed 'players'\n"
            "),\n"
            "\n"
            "cleaned as (\n"
            "    select\n"
            '        trim("Player")                          as player_name,  -- remove espaços\n'
            '        upper(trim("Team"))                     as team_abbr,   -- padroniza maiúsculo\n'
            '        upper(trim("Pos"))                      as position,    -- G, F, C...\n'
            "        nullif(trim(\"Age\"::text), '')::integer  as age          -- string → int\n"
            "    from source\n"
            "    where trim(\"Player\") != 'Player'            -- remove linhas de cabeçalho repetidas\n"
            ")\n"
            "\n"
            "select * from cleaned"
        )
    )
    story.append(sp(6))

    story.append(h3("Padrões que aparecem aqui e por que existem:"))
    staging_patterns = [
        ["Padrão", "Exemplo", "Motivo"],
        [
            "{{ ref() }}",
            "ref('players')",
            "Cria dependência no DAG. dbt garante que o seed existe antes de rodar este modelo.",
        ],
        [
            "trim()",
            'trim("Player")',
            "BBR às vezes inclui espaços em branco no início/fim de strings.",
        ],
        [
            "upper()",
            'upper(trim("Team"))',
            "Padroniza para comparações case-insensitive downstream.",
        ],
        [
            "nullif()",
            "nullif(trim(x), '')",
            "Converte string vazia em NULL, que é o valor correto semanticamente.",
        ],
        [
            "::integer",
            "trim(x)::integer",
            "Cast explícito de tipo — seeds carregam tudo como texto, precisamos tipar.",
        ],
        [
            "where != 'Player'",
            "trim(\"Player\") != 'Player'",
            "BBR repete a linha de cabeçalho a cada ~100 linhas na tabela HTML paginada.",
        ],
        [
            "Colunas entre aspas",
            '"Player", "Team"',
            "Os nomes no PostgreSQL são case-sensitive quando criados com quote_columns: true.",
        ],
    ]
    story.append(colored_table(staging_patterns, [2.8 * cm, 3.5 * cm, 10.2 * cm]))
    story.append(PageBreak())

    story.append(h2("4.4 stg_bbr__player_stats.sql — O Desafio das Colunas Especiais"))
    story.append(
        p(
            "Basketball Reference usa nomes de colunas com caracteres que são inválidos em SQL: "
            "<b>FG%</b> (símbolo de porcentagem), <b>3P</b> (começa com número), <b>eFG%</b> (mistura tudo). "
            "Esses nomes foram renomeados no scraper Python antes de salvar o CSV "
            "para que o dbt seed pudesse carregar sem erros."
        )
    )
    story.append(sp(4))

    renomes = [
        ["Nome original BBR", "Nome no CSV/seed", "Motivo da renomeação"],
        ["FG%", "fg_pct", "% é operador em SQL"],
        ["3P", "three_p", "Nomes não podem começar com dígito em SQL"],
        ["3PA", "three_pa", "Mesmo motivo"],
        ["3P%", "three_p_pct", "Ambos os problemas"],
        ["2P", "two_p", "Começa com dígito"],
        ["2PA", "two_pa", "Começa com dígito"],
        ["2P%", "two_p_pct", "Ambos os problemas"],
        ["eFG%", "efg_pct", "% é operador em SQL"],
        ["FT%", "ft_pct", "% é operador em SQL"],
        ["W/L%", "wl_pct", "/ e % são operadores em SQL (no team.csv)"],
    ]
    story.append(colored_table(renomes, [3.5 * cm, 3.5 * cm, 9.5 * cm]))
    story.append(sp(8))

    story.append(h2("4.5 stg_bbr__teams.sql — Dados Históricos de Franquias"))
    story.append(
        p(
            "O BBR lista a história de cada franquia com múltiplas eras (ex: Oklahoma City Thunder "
            "tem uma era como Seattle SuperSonics). A staging não filtra isso — ela limpa os tipos "
            "e repassa todas as linhas. A lógica de filtrar só a era atual fica em dim_team (marts)."
        )
    )
    story.append(sp(4))
    story.append(
        callout(
            "💡 <b>Princípio de design:</b> a staging não sabe o que é 'correto' do ponto de vista "
            "de negócio — ela só sabe o que está na fonte. Decisões de negócio ('quero só a era atual') "
            "ficam nas camadas downstream onde são explícitas e documentadas."
        )
    )
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PARTE 5 — INTERMEDIATE LAYER
    # ════════════════════════════════════════════════════════════════════════
    story += section_divider("PARTE 5 — Intermediate Layer (Regras de Negócio)")

    story.append(h2("5.1 O Que É a Camada Intermediate"))
    story.append(
        p(
            "A intermediate layer existe para lógica de negócio que é <b>reutilizada por múltiplos marts</b> "
            "mas não pertence à staging (que não tem lógica) e não pertence diretamente ao mart "
            "(que ficaria muito complexo). É o equivalente de uma função auxiliar no código Python."
        )
    )
    story.append(sp(4))
    story.append(
        p(
            "Convenção de nome: <b>int_[domínio]__[propósito].sql</b><br/>"
            "Exemplos: int_players__deduped, int_player_stats__season_totals"
        )
    )
    story.append(sp(8))

    story.append(h2("5.2 O Problema do Jogador Trocado — A Regra de Negócio Principal"))
    story.append(
        p(
            "Este é o exemplo perfeito do tipo de problema que aparece em dados reais "
            "e que entrevistadores adoram explorar. "
            "Quando um jogador é trocado de time durante a temporada, o Basketball Reference "
            "registra <b>múltiplas linhas</b> para ele:"
        )
    )
    story.append(sp(4))

    traded_example = [
        ["Player", "Team", "G", "PTS"],
        ["Dennis Schröder", "BRK", "12", "12.1"],
        ["Dennis Schröder", "GSW", "28", "9.3"],
        ["Dennis Schröder", "DET", "31", "14.2"],
        ["Dennis Schröder", "3TM", "71", "11.8 ← linha agregada (3 times)"],
    ]
    t = colored_table(traded_example, [4.5 * cm, 2 * cm, 1.5 * cm, 9 * cm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#FFF3CD")),
                ("FONTNAME", (0, 4), (-1, 4), "Helvetica-Bold"),
            ]
        )
    )
    story.append(t)
    story.append(sp(6))

    story.append(
        p(
            "Se você somar todos os jogos de Dennis Schröder, vai contar 142 jogos (12+28+31+71) "
            "quando a temporada tem 82 jogos no máximo. O registro <b>3TM</b> (3 times) é o agregado "
            "correto — 71 jogos, média ponderada de pontos. "
            "<b>Histórico:</b> o BBR usava 'TOT' para isso, mas a partir de 2024-25 passou a usar "
            "'2TM', '3TM', '4TM' conforme o número de times."
        )
    )
    story.append(sp(6))

    story.append(h3("A solução implementada em int_players__deduped.sql:"))
    story.append(
        code(
            "traded_players as (\n"
            "    -- Identifica jogadores que têm linha de agregado\n"
            "    select distinct player_name\n"
            "    from players\n"
            "    where team_abbr = 'TOT'           -- formato antigo\n"
            "       or team_abbr ~ '^\\d+TM$'      -- formato novo: 2TM, 3TM, 4TM...\n"
            "),\n"
            "\n"
            "deduped as (\n"
            "    select p.*\n"
            "    from players p\n"
            "    left join traded_players t using (player_name)\n"
            "    where\n"
            "        t.player_name is null           -- não foi trocado: mantém a linha única\n"
            "        or p.team_abbr = 'TOT'          -- foi trocado: mantém só o agregado\n"
            "        or p.team_abbr ~ '^\\d+TM$'\n"
            ")"
        )
    )
    story.append(sp(6))

    story.append(
        interview_q(
            "Como você lidaria com dados duplicados de um jogador trocado de time?"
        )
    )
    story.append(
        interview_a(
            "No Basketball Reference, cada jogador trocado tem N+1 linhas: uma por time e uma com o "
            "total agregado (TOT/NTM). Para análise de temporada completa, o correto é manter apenas "
            "o agregado, que já tem a média ponderada pelo número de jogos em cada time. "
            "Implementei isso com um LEFT JOIN para identificar jogadores com linha de agregado "
            "e filtrei para manter apenas essa linha. O desafio extra foi que o BBR mudou a "
            "nomenclatura de 'TOT' para '2TM/3TM' na temporada atual — resolvi com regex '^\\d+TM$' "
            "para ser compatível com ambos os formatos."
        )
    )
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PARTE 6 — MARTS LAYER
    # ════════════════════════════════════════════════════════════════════════
    story += section_divider("PARTE 6 — Marts Layer (Modelo Dimensional)")

    story.append(h2("6.1 Modelagem Dimensional — dim_ e fct_"))
    story.append(
        p(
            "A camada marts implementa o <b>modelo dimensional</b> (também chamado de Star Schema), "
            "o padrão consagrado para data warehouses analíticos. Foi formalizado por Ralph Kimball "
            "nos anos 90 e continua sendo o padrão dominante em 2025."
        )
    )
    story.append(sp(4))

    dim_fct = [
        ["Tipo", "Prefixo", "O que contém", "Características"],
        [
            "Dimension",
            "dim_",
            "Atributos descritivos das entidades",
            "Muda raramente, tem surrogate key, enriquece análises",
        ],
        [
            "Fact",
            "fct_",
            "Eventos/métricas mensuráveis",
            "Cresce constantemente, tem FKs para dimensions, é o grain da análise",
        ],
    ]
    story.append(colored_table(dim_fct, [2 * cm, 1.8 * cm, 5.5 * cm, 7 * cm]))
    story.append(sp(6))

    story.append(h2("6.2 dim_player.sql — Dimensão do Jogador"))
    story.append(
        p(
            "Uma linha por jogador ativo na temporada. Contém atributos que descrevem o jogador: "
            "nome, posição, idade, time atual, conferência, divisão. "
            "Não contém estatísticas — essas ficam na fct_."
        )
    )
    story.append(sp(4))

    story.append(h3("Lógica de resolução do time atual para jogadores trocados:"))
    story.append(
        code(
            "-- Jogadores trocados têm team_abbr = '3TM' na tabela deduped.\n"
            "-- Precisamos saber em qual time eles TERMINARAM a temporada.\n"
            "-- Buscamos o time com mais jogos nas linhas por-time (excluindo o agregado).\n"
            "\n"
            "last_team as (\n"
            "    select player_name, team_abbr as last_team_abbr\n"
            "    from (\n"
            "        select player_name, team_abbr, games_played,\n"
            "               row_number() over (\n"
            "                   partition by player_name\n"
            "                   order by games_played desc  -- time com mais jogos = último\n"
            "               ) as rn\n"
            "        from stg_bbr__player_stats\n"
            "        where team_abbr != 'TOT'\n"
            "          and team_abbr !~ '^\\d+TM$'  -- exclui as linhas de agregado\n"
            "    ) ranked\n"
            "    where rn = 1\n"
            ")"
        )
    )
    story.append(sp(6))

    story.append(h2("6.3 dim_team.sql — Dimensão do Time"))
    story.append(
        p(
            "30 linhas — uma por franquia ativa da NBA. Combina o seed estático team_info "
            "(conferência, divisão — dados que o BBR não fornece diretamente) com os dados "
            "históricos de vitórias/derrotas do BBR teams page."
        )
    )
    story.append(sp(4))

    story.append(h3("Desafio: múltiplas eras históricas por franquia"))
    story.append(
        p(
            "O BBR lista cada era de uma franquia separadamente. Por exemplo, o Boston Celtics "
            "tem múltiplas linhas com season_to = '2025-26' (era de 1946-47 até hoje, etc.). "
            "A solução foi usar ROW_NUMBER() para selecionar apenas a linha com "
            "mais jogos disputados (o record all-time, que inclui toda a história)."
        )
    )
    story.append(sp(6))

    story.append(h2("6.4 fct_player_season_stats.sql — A Tabela Fato"))
    story.append(
        p(
            "<b>Grain (granularidade)</b>: uma linha por jogador por temporada. "
            "Este é o conceito mais importante do modelo dimensional — "
            "cada linha da tabela fato representa exatamente um evento/medição de nível específico."
        )
    )
    story.append(sp(4))

    fct_cols = [
        ["Coluna", "Tipo", "O que representa"],
        ["fact_key", "TEXT (MD5)", "Surrogate key da linha fato"],
        ["player_key", "TEXT (MD5)", "FK → dim_player"],
        ["team_key", "TEXT (MD5)", "FK → dim_team"],
        ["season", "TEXT", "Degenerate dimension: '2024-25'"],
        ["games_played", "INTEGER", "Fact: total de jogos"],
        ["points_per_game", "NUMERIC", "Fact: média de pontos"],
        ["fg_pct", "NUMERIC", "Fact: porcentagem de arremessos"],
        ["... (25 colunas)", "NUMERIC", "Todas as stats per-game do BBR"],
    ]
    story.append(colored_table(fct_cols, [3.5 * cm, 3 * cm, 10 * cm]))
    story.append(sp(6))

    story.append(
        callout(
            "💡 <b>Degenerate Dimension (season):</b> O campo 'season' é uma dimensão degenerada — "
            "um atributo descritivo que não vale a pena colocar numa tabela dim_season separada "
            "porque só tem um valor neste projeto (2024-25). Em um data warehouse com múltiplas "
            "temporadas, existiria uma dim_season com atributos como playoffs_year, all_star_location, etc."
        )
    )
    story.append(PageBreak())

    story.append(
        interview_q("O que é Star Schema e por que você escolheu esse modelo?")
    )
    story.append(
        interview_a(
            "Star Schema é um modelo dimensional onde uma tabela fato central se conecta a "
            "múltiplas tabelas dimensão por chaves estrangeiras. A forma do diagrama ER lembra "
            "uma estrela — a fato no centro, as dims nas pontas. Escolhi esse modelo porque "
            "(1) facilita queries analíticas intuitivas — analistas fazem JOIN fct com dim e "
            "groupam por qualquer atributo dimensional; (2) queries de agregação são rápidas "
            "porque a tabela fato tem só números e FKs; (3) é o padrão que ferramentas de BI "
            "como Metabase e Looker entendem nativamente. A alternativa seria um modelo 3NF "
            "(normalização completa), que é ótimo para sistemas transacionais mas ruim para "
            "analytics porque exige muitos JOINs."
        )
    )
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PARTE 7 — TESTES E YAML
    # ════════════════════════════════════════════════════════════════════════
    story += section_divider("PARTE 7 — Testes de Qualidade de Dados")

    story.append(h2("7.1 Por Que Testes em Dados São Críticos"))
    story.append(
        p(
            "Diferente de código de software, onde um bug geralmente causa um erro imediato, "
            "bugs em dados são silenciosos. Um dashboard mostrando o número errado de pontos "
            "por jogo pode enganar um analista por semanas antes de alguém perceber. "
            "Testes de dados são a única forma de detectar isso automaticamente."
        )
    )
    story.append(sp(4))
    story.append(
        p(
            "O dbt oferece <b>testes genéricos</b> que você declara em YAML — não precisa escrever SQL. "
            "O dbt gera o SQL de teste automaticamente."
        )
    )
    story.append(sp(6))

    story.append(h2("7.2 Os Quatro Tipos de Teste Usados no Projeto"))

    testes = [
        ["Teste", "O que valida", "Exemplo no projeto"],
        [
            "unique",
            "Nenhum valor se repete na coluna",
            "player_key em dim_player deve ser único",
        ],
        ["not_null", "Nenhum valor nulo na coluna", "player_name em todas as tabelas"],
        [
            "accepted_values",
            "Coluna só contém valores de uma lista",
            "conference só aceita 'East' ou 'West'",
        ],
        [
            "relationships",
            "FK existe na tabela referenciada (integridade referencial)",
            "player_key em fct deve existir em dim_player",
        ],
    ]
    story.append(colored_table(testes, [3 * cm, 5.5 * cm, 8 * cm]))
    story.append(sp(6))

    story.append(h2("7.3 Como Declarar um Teste (schema YAML)"))
    story.append(sp(4))
    story.append(
        code(
            "# models/marts/_marts__models.yml\n"
            "models:\n"
            "  - name: dim_player\n"
            "    columns:\n"
            "      - name: player_key\n"
            "        data_tests:\n"
            "          - unique      # ← dbt gera: SELECT count(*) WHERE count > 1\n"
            "          - not_null    # ← dbt gera: SELECT count(*) WHERE player_key IS NULL\n"
            "\n"
            "      - name: conference\n"
            "        data_tests:\n"
            "          - accepted_values:\n"
            "              values: ['East', 'West']  # falha se encontrar outro valor\n"
            "\n"
            "  - name: fct_player_season_stats\n"
            "    columns:\n"
            "      - name: player_key\n"
            "        data_tests:\n"
            "          - relationships:\n"
            "              to: ref('dim_player')  # verifica que toda FK existe na dim\n"
            "              field: player_key"
        )
    )
    story.append(sp(6))

    story.append(h2("7.4 Rodando os Testes"))
    story.append(
        code(
            "dbt test --profiles-dir .dbt                    # todos os testes\n"
            "dbt test --profiles-dir .dbt --select dim_player  # só um modelo\n"
            "dbt test --profiles-dir .dbt --select test_type:unique  # só os unique"
        )
    )
    story.append(sp(4))
    story.append(
        p(
            "No nosso projeto: <b>26 testes passando</b>. "
            "Cada vez que os dados são atualizados (novo scraping), "
            "os testes são re-executados para garantir que nada quebrou."
        )
    )
    story.append(sp(6))

    story.append(interview_q("Como você garante qualidade de dados no seu pipeline?"))
    story.append(
        interview_a(
            "No dbt implemento testes declarativos em YAML para cada camada: unique e not_null "
            "nas chaves primárias, accepted_values para enums (conferência Leste/Oeste), e "
            "relationships para integridade referencial entre fcts e dims. "
            "Isso captura 80% dos problemas comuns de qualidade. Para dados de produção adicionaria "
            "também testes de volume (número de linhas dentro de um range esperado) e "
            "testes de freshness (dados não podem ter mais de X horas). "
            "Em pipelines mais maduros usaria ferramentas como Great Expectations ou "
            "Soda Core para testes mais sofisticados."
        )
    )
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PARTE 8 — PYTHON SCRAPING
    # ════════════════════════════════════════════════════════════════════════
    story += section_divider("PARTE 8 — Scrapers Python (src/scraping/)")

    story.append(h2("8.1 Por Que Selenium e Não requests"))
    story.append(
        p(
            "A primeira tentativa natural é fazer requests.get(url) para pegar o HTML da página. "
            "O Basketball Reference retorna <b>HTTP 403 Forbidden</b> para qualquer cliente "
            "que não pareça um navegador real. Eles detectam pelo User-Agent e pelo comportamento "
            "de não executar JavaScript."
        )
    )
    story.append(sp(4))
    story.append(
        p(
            "Selenium resolve isso ao controlar um navegador real (Chromium) — o site não consegue "
            "distinguir do acesso humano. A desvantagem é lentidão (~8 segundos por página) "
            "e dependência de um ambiente com GUI (resolvido com modo headless)."
        )
    )
    story.append(sp(6))

    story.append(h2("8.2 Estrutura do Módulo src/scraping/"))

    estrutura = [
        ["Arquivo", "Função"],
        [
            "common/browser.py",
            "Configura o Selenium: caminhos do Chromium snap, modo headless, sleep de 8s",
        ],
        [
            "common/parsing.py",
            "Função uncomment_tables(): BBR esconde tabelas em comentários HTML",
        ],
        ["players.py", "Extrai roster (Player, Age, Team, Pos) → seeds/players.csv"],
        [
            "stats.py",
            "Extrai stats completas → seeds/players_stats.csv (com renomeações)",
        ],
        ["teams.py", "Extrai histórico de franquias → seeds/team.csv"],
        [
            "contracts.py",
            "Extrai contratos → seeds/contracts.csv (armazenado para uso futuro)",
        ],
        [
            "run_all.py",
            "Orquestrador: roda todos os scrapers em sequência com log de resultado",
        ],
    ]
    story.append(colored_table(estrutura, [4 * cm, 12.5 * cm]))
    story.append(sp(6))

    story.append(h2("8.3 O Truque das Tabelas em Comentário HTML"))
    story.append(
        p(
            "BBR esconde as tabelas de dados dentro de comentários HTML para dificultar scraping: "
            "<b>&lt;!-- &lt;table id='per_game_stats'&gt;...&lt;/table&gt; --&gt;</b>. "
            "BeautifulSoup ignora comentários por padrão — a tabela simplesmente não aparece."
        )
    )
    story.append(sp(4))
    story.append(
        code(
            "def uncomment_tables(soup):\n"
            "    from bs4 import Comment\n"
            "    for c in soup.find_all(string=lambda t: isinstance(t, Comment)):\n"
            "        inner = BeautifulSoup(str(c), 'lxml')  # parseia o conteúdo do comentário\n"
            "        if inner.find('table'):                 # se tiver tabela dentro\n"
            "            c.replace_with(inner)               # substitui o comentário pela tabela\n"
            "    return soup\n"
            "\n"
            "# ATENÇÃO: BeautifulSoup 4.13 quebrou soup.append() — retorna lista vazia.\n"
            "# A forma correta é c.replace_with(), que funciona em todas as versões."
        )
    )
    story.append(sp(6))

    story.append(h2("8.4 Configuração do Chromium no WSL (Ubuntu Snap)"))
    story.append(
        p(
            "No Windows Subsystem for Linux (WSL) com Ubuntu, o Chromium é instalado via Snap "
            "e seus executáveis ficam em caminhos não-padrão que o webdriver-manager não encontra."
        )
    )
    story.append(
        code(
            "CHROME_BINARY    = '/usr/bin/chromium-browser'      # o navegador\n"
            "CHROMEDRIVER_PATH = '/snap/bin/chromium.chromedriver'  # o driver\n"
            "\n"
            "opts = Options()\n"
            "opts.binary_location = CHROME_BINARY\n"
            "opts.add_argument('--headless=new')     # sem janela gráfica\n"
            "opts.add_argument('--no-sandbox')       # necessário no WSL\n"
            "service = Service(executable_path=CHROMEDRIVER_PATH)\n"
            "driver = webdriver.Chrome(service=service, options=opts)"
        )
    )
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PARTE 9 — ENTREVISTA
    # ════════════════════════════════════════════════════════════════════════
    story += section_divider("PARTE 9 — Como Falar Sobre o Projeto em Entrevista")

    story.append(h2("9.1 O Pitch de 2 Minutos (Elevator Pitch)"))
    story.append(
        callout(
            '"Construí um pipeline de dados end-to-end para análise de estatísticas da NBA. '
            "Fiz scraping automatizado do Basketball Reference com Python e Selenium, "
            "porque o site bloqueia requests diretos. Os dados são carregados no PostgreSQL "
            "e transformados com dbt Core seguindo arquitetura em três camadas: "
            "staging para limpeza, intermediate para regras de negócio como de-duplicação "
            "de jogadores trocados, e marts com modelo dimensional (Star Schema) para análise. "
            "O projeto tem 26 testes automatizados de qualidade de dados e documentação "
            'gerada automaticamente no YAML."'
        )
    )
    story.append(sp(8))

    story.append(h2("9.2 Perguntas Técnicas — Nível Pleno"))

    story.append(interview_q("Qual a diferença entre ETL e ELT?"))
    story.append(
        interview_a(
            "ETL (Extract-Transform-Load) transforma os dados antes de carregar no destino final — "
            "era necessário quando armazenamento era caro. ELT (Extract-Load-Transform) carrega os dados "
            "brutos primeiro e transforma dentro do data warehouse — possível com o barateamento de "
            "armazenamento e aumento do poder computacional dos bancos modernos. dbt é fundamentalmente "
            "uma ferramenta ELT: os dados chegam no PostgreSQL via seed, e o dbt transforma dentro do banco."
        )
    )
    story.append(sp(4))

    story.append(
        interview_q("O que é materialização no dbt? Quando usar VIEW vs TABLE?")
    )
    story.append(
        interview_a(
            "Materialização é como o dbt persiste o resultado de um modelo no banco. "
            "VIEW não armazena dados — executa a query na hora da consulta, sem custo de storage, "
            "mas pode ser lenta se consultada frequentemente. TABLE persiste os dados fisicamente — "
            "consulta rápida, mas ocupa storage e precisa ser reconstruída a cada run. "
            "No projeto: staging e intermediate são VIEW (mudam com frequência, raramente consultadas diretamente), "
            "marts são TABLE (consultadas por analistas, velocidade importa). "
            "Existe também INCREMENTAL (só processa novos registros) e EPHEMERAL (CTE inline, sem objeto no banco)."
        )
    )
    story.append(sp(4))

    story.append(interview_q("Como funciona o {{ ref() }} no dbt?"))
    story.append(
        interview_a(
            "ref() é a função central do dbt. Quando você escreve ref('stg_bbr__players'), "
            "o dbt (1) resolve para o nome completo da tabela/view no banco (schema + nome), "
            "(2) registra uma dependência no DAG — este modelo depende de stg_bbr__players, "
            "garantindo que ele exista antes de tentar criar o atual. "
            "É o que permite ao dbt calcular a ordem correta de execução e paralelizar "
            "modelos independentes. source() serve para referenciar tabelas externas não gerenciadas pelo dbt."
        )
    )
    story.append(sp(4))

    story.append(interview_q("O que é um surrogate key e por que você usou MD5?"))
    story.append(
        interview_a(
            "Surrogate key é uma chave primária artificial — gerada pelo sistema, não derivada dos dados reais. "
            "Usamos MD5(player_name) porque: (1) é determinístico — o mesmo nome sempre gera o mesmo hash, "
            "permitindo joins sem precisar de um sequence ou UUID centralizado; "
            "(2) é compacto — 32 chars vs nomes de comprimento variável; "
            "(3) é estável mesmo que a lógica de geração migre entre sistemas. "
            "A alternativa seria usar SERIAL/IDENTITY no PostgreSQL, mas isso complica joins "
            "entre modelos que não passam pela mesma transação."
        )
    )
    story.append(PageBreak())

    story.append(h2("9.3 Perguntas Técnicas — Nível Sênior"))

    story.append(
        interview_q("Como você escalaria esse pipeline para múltiplas temporadas?")
    )
    story.append(
        interview_a(
            "Adicionaria uma coluna season em todos os seeds e modelos, e usaria materialização "
            "INCREMENTAL no dbt para processar apenas dados novos. No staging, adicionaria "
            "um filtro {{ this.filters }} para ler só CSVs da temporada nova. "
            "Na fct_, a chave seria (player_name, season) em vez de só player_name. "
            "Para dim_player, implementaria SCD Type 2 (Slowly Changing Dimension) "
            "para rastrear mudanças de time entre temporadas — cada mudança gera uma nova "
            "versão do registro com effective_from/effective_to."
        )
    )
    story.append(sp(4))

    story.append(
        interview_q(
            "Quais problemas de qualidade de dados você encontrou e como resolveu?"
        )
    )
    story.append(
        interview_a(
            "Três principais: (1) BBR repete a linha de cabeçalho a cada página — "
            "filtrei com WHERE player != 'Player' no staging. "
            "(2) Jogadores trocados aparecem múltiplas vezes — resolvi com CTE de de-duplicação "
            "na camada intermediate usando o padrão NTM. "
            "(3) BBR mudou nomenclatura de 'TOT' para '2TM/3TM' na temporada atual — "
            "descoberto apenas quando os testes unique falharam com 81 duplicatas. "
            "Resolvi com regex '^\\d+TM$' para capturar ambos os formatos. "
            "Isso mostra a importância dos testes — sem eles, os dados estariam errados silenciosamente."
        )
    )
    story.append(sp(4))

    story.append(
        interview_q("Como você organizaria CI/CD para um pipeline dbt em produção?")
    )
    story.append(
        interview_a(
            "No GitHub Actions: (1) PR → dbt compile (valida sintaxe) + dbt test em um schema de CI "
            "isolado com dados de sample. (2) Merge em main → dbt run + dbt test completo em staging "
            "environment. (3) Aprovação manual → deploy em produção. "
            "Usaria dbt slim CI (--state flag) para rodar apenas modelos que mudaram, "
            "reduzindo tempo de execução. Para o agendamento, integraria com Airflow ou Dagster "
            "em vez de cron — eles gerenciam retries, alertas e dependências entre pipelines."
        )
    )
    story.append(sp(4))

    story.append(interview_q("Por que PostgreSQL em vez de DuckDB ou Snowflake?"))
    story.append(
        interview_a(
            "DuckDB seria mais simples para desenvolvimento local — não precisa de servidor, "
            "lê CSVs nativamente. Escolhi PostgreSQL para demonstrar setup de produção: "
            "configuração de conexão com credentials via env_var, separação de schemas, "
            "compatibilidade com ferramentas BI padrão de mercado. "
            "Em produção real com volume, usaria BigQuery ou Snowflake — o dbt suporta ambos "
            "com apenas mudança no profiles.yml (type: bigquery ou type: snowflake)."
        )
    )
    story.append(PageBreak())

    story.append(h2("9.4 Perguntas Comportamentais Sobre o Projeto"))

    story.append(interview_q("Qual foi o maior desafio técnico do projeto?"))
    story.append(
        interview_a(
            "A detecção da mudança de nomenclatura do BBR de 'TOT' para 'NTM' durante o desenvolvimento. "
            "Os modelos compilavam e rodavam sem erro — só os testes de unicidade revelaram 81 duplicatas "
            "inesperadas. Investiguei consultando o banco diretamente, descobri o padrão '3TM' e "
            "atualizei a regex de detecção. Isso reforçou a importância de testes automatizados: "
            "sem eles, o dashboard mostraria estatísticas infladas para ~80 jogadores e ninguém perceberia."
        )
    )
    story.append(sp(4))

    story.append(interview_q("Por que você escolheu essa estrutura de camadas?"))
    story.append(
        interview_a(
            "A separação staging/intermediate/marts vem do dbt best practices guide e da experiência "
            "coletiva da comunidade. O princípio central é: cada camada tem uma responsabilidade única "
            "e imutável. Staging só limpa, intermediate só aplica regras de negócio reutilizáveis, "
            "marts expõem para o usuário final. Se o Basketball Reference mudar o nome de uma coluna, "
            "só staging precisa mudar — intermediate e marts ficam intactos. "
            "Sem essa separação, uma mudança na fonte pode quebrar múltiplos modelos de forma não-óbvia."
        )
    )
    story.append(sp(6))

    story.append(h2("9.5 Red Flags Para Evitar na Entrevista"))

    red_flags = [
        ["❌ O que não dizer", "✅ O que dizer no lugar"],
        [
            "'Eu segui um tutorial'",
            "'Enfrentei e resolvi esses problemas específicos...'",
        ],
        [
            "'Não sei por que funciona assim'",
            "'A razão para essa escolha foi...' (explique o trade-off)",
        ],
        [
            "'dbt é tipo um ORM'",
            "'dbt é um transformador SQL com gestão de dependências e testes'",
        ],
        [
            "'Não testei'",
            "'Tenho 26 testes cobrindo unicidade, not_null e integridade referencial'",
        ],
        [
            "'É um projeto pessoal simples'",
            "'Implementei padrões de produção: separação de ambientes, credenciais via env_var, CI com testes'",
        ],
    ]
    story.append(
        colored_table(
            red_flags, [(W - 4 * cm) * 0.42, (W - 4 * cm) * 0.58], header_bg=RED
        )
    )
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PARTE 10 — GLOSSÁRIO E REFERÊNCIAS
    # ════════════════════════════════════════════════════════════════════════
    story += section_divider("PARTE 10 — Glossário e Próximos Passos")

    story.append(h2("10.1 Glossário de Termos"))

    glossario = [
        ["Termo", "Definição"],
        [
            "DAG",
            "Directed Acyclic Graph — grafo de dependências sem ciclos. No dbt, define a ordem de execução.",
        ],
        [
            "ELT",
            "Extract-Load-Transform — dados são carregados brutos no banco e transformados lá dentro.",
        ],
        [
            "Grain",
            "A granularidade de uma tabela fato — o que cada linha representa (ex: 1 linha = 1 jogador por temporada).",
        ],
        [
            "Jinja2",
            "Sistema de templates Python usado pelo dbt para lógica em SQL ({{ ref() }}, {% if %}, etc.)",
        ],
        [
            "Lineage",
            "O mapa de dependências entre modelos — mostra de onde os dados vêm e para onde vão.",
        ],
        ["Macro", "Função Jinja reutilizável no dbt — como generate_surrogate_key()."],
        [
            "Materialização",
            "Como o dbt persiste um modelo: view, table, incremental ou ephemeral.",
        ],
        [
            "Profile",
            "Arquivo de configuração com credenciais de conexão ao banco (.dbt/profiles.yml).",
        ],
        [
            "ref()",
            "Função dbt que cria dependência entre modelos e resolve o nome completo da tabela.",
        ],
        [
            "Schema",
            "Namespace no PostgreSQL que agrupa tabelas (analytics_raw, analytics_marts, etc.)",
        ],
        [
            "Seed",
            "Arquivo CSV carregado no banco pelo dbt seed — usado para dados de referência estáticos.",
        ],
        [
            "SCD Type 2",
            "Slowly Changing Dimension — técnica para rastrear histórico de mudanças em dimensões.",
        ],
        [
            "Surrogate Key",
            "ID artificial gerado pelo sistema (MD5, UUID) — independente dos dados de negócio.",
        ],
        [
            "Star Schema",
            "Modelo dimensional com tabela fato central e tabelas dim nas bordas.",
        ],
        [
            "TOT / NTM",
            "Abreviações BBR para jogadores trocados: TOT (legado) = Total, NTM = N Times.",
        ],
    ]
    story.append(colored_table(glossario, [3.5 * cm, 13 * cm]))
    story.append(sp(8))

    story.append(h2("10.2 Próximos Passos para Evoluir o Projeto"))

    proximos = [
        ["Evolução", "Dificuldade", "O que demonstra"],
        [
            "Adicionar temporadas anteriores (SCD Type 2)",
            "⭐⭐⭐",
            "Modelagem temporal avançada",
        ],
        ["Agendamento com Airflow ou Prefect", "⭐⭐⭐", "Orquestração de pipelines"],
        [
            "Dashboard com Metabase ou Superset",
            "⭐⭐",
            "Entrega de valor para o usuário final",
        ],
        [
            "CI/CD com GitHub Actions (dbt slim CI)",
            "⭐⭐⭐",
            "Maturidade de engenharia",
        ],
        [
            "Modelo incremental (só processa dados novos)",
            "⭐⭐⭐",
            "Performance em escala",
        ],
        ["API de contratos para análise salarial", "⭐⭐", "Expansão de domínio"],
        [
            "dbt docs serve + publicação online",
            "⭐",
            "Documentação acessível para recrutadores",
        ],
        ["Migrar para DuckDB (mais simples de demonstrar)", "⭐", "Portabilidade"],
        ["Testes customizados com macros dbt", "⭐⭐⭐", "Qualidade de dados avançada"],
    ]
    story.append(colored_table(proximos, [7 * cm, 2.5 * cm, 7 * cm]))
    story.append(sp(8))

    story.append(h2("10.3 Recursos Para Estudar Mais"))
    story.append(
        b(
            "<b>Documentação oficial dbt:</b> docs.getdbt.com — a mais completa e bem escrita"
        )
    )
    story.append(b("<b>dbt Learn:</b> courses.getdbt.com — curso gratuito oficial"))
    story.append(
        b(
            "<b>Livro The Data Warehouse Toolkit</b> (Kimball) — fundamentos do modelo dimensional"
        )
    )
    story.append(
        b(
            "<b>dbt Style Guide:</b> github.com/dbt-labs/corp/blob/main/dbt_style_guide.md"
        )
    )
    story.append(
        b(
            "<b>Comunidade dbt Slack:</b> getdbt.com/community — 50k+ membros, muito ativo"
        )
    )
    story.append(sp(12))

    # Rodapé final
    story.append(hr(ORANGE, 2))
    story.append(
        Paragraph(
            "NBA Analytics Portfolio — Projeto completo disponível no GitHub",
            ParagraphStyle(
                "footer_final",
                fontSize=10,
                textColor=GRAY,
                fontName="Helvetica",
                alignment=TA_CENTER,
            ),
        )
    )
    story.append(
        Paragraph(
            "dbt Core 1.9 · PostgreSQL 17 · Python 3.12 · Selenium 4",
            ParagraphStyle(
                "footer_final2",
                fontSize=9,
                textColor=GRAY,
                fontName="Helvetica",
                alignment=TA_CENTER,
            ),
        )
    )

    return story


# ── BUILD DO PDF ─────────────────────────────────────────────────────────────
def build_pdf():
    frame = Frame(1.5 * cm, 1.8 * cm, W - 3 * cm, H - 3.2 * cm, id="normal")
    template = PageTemplate(id="main", frames=[frame], onPage=on_page)
    doc = BaseDocTemplate(
        OUTPUT,
        pagesize=A4,
        pageTemplates=[template],
        title="NBA Analytics — Guia Completo dbt + PostgreSQL",
        author="Henri",
        subject="Portfolio de Engenharia de Dados",
    )

    story = build_content()
    doc.build(story)
    print(f"\n✅ PDF gerado com sucesso: {OUTPUT}")
    import os

    size_mb = os.path.getsize(OUTPUT) / 1024 / 1024
    print(f"   Tamanho: {size_mb:.2f} MB")


if __name__ == "__main__":
    build_pdf()
