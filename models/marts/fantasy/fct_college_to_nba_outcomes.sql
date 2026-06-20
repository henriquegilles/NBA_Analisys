-- fct_college_to_nba_outcomes
-- Grão: 1 linha por prospecto histórico que chegou à NBA (espinha dorsal D-05).
--
-- Junta o PERFIL college (preditor — última temporada, por-40 + contexto +
-- trajetória) ao DESFECHO NBA (alvo — médias de carreira por-jogo + valor),
-- via int_prospect__nba_bridge. É a base de "perfil college → como rendeu":
-- fct_prospect_scouting projeta um prospecto novo pela média desta tabela
-- sobre seus comps.
--
-- Desfecho = média de carreira (D-11). Cobre 3 das 6 categorias (pts/reb/ast)
-- + WS/BPM/VORP — limitação da fonte `draft` (sem stocks/3PM/TOV de carreira).

with bridge as (
    select *
    from {{ ref('int_prospect__nba_bridge') }}
    where n_matches = 1        -- ignora ambíguos (override manual fica p/ D-09)
      and reached_nba          -- só quem efetivamente jogou na NBA
),

profile as (
    select cbb_id, archetype, position, class, class_rank,
           pts_per_40, trb_per_40, ast_per_40, stocks_per_40, three_p_per_40, tov_per_40,
           ts_pct, usg_pct, team_sos, rsci_rank, trajectory_flag
    from (
        select *, row_number() over (partition by cbb_id order by season desc) as rn
        from {{ ref('int_prospect__college_stats') }}
    ) s
    where rn = 1
)

select
    -- Identidade
    b.cbb_id,
    b.player_name,
    b.college_school,
    b.last_college_season,
    b.draft_year,
    b.pick,

    -- Preditor: perfil college (última temporada)
    pr.archetype,
    pr.class_rank,
    pr.pts_per_40,
    pr.trb_per_40,
    pr.ast_per_40,
    pr.stocks_per_40,
    pr.three_p_per_40,
    pr.tov_per_40,
    pr.ts_pct,
    pr.usg_pct,
    pr.team_sos,
    pr.trajectory_flag,

    -- Alvo: desfecho NBA (média de carreira — D-11)
    b.nba_career_games,
    b.nba_pg_pts,
    b.nba_pg_trb,
    b.nba_pg_ast,
    b.nba_win_shares,
    b.nba_bpm,
    b.nba_vorp

from bridge b
join profile pr using (cbb_id)
