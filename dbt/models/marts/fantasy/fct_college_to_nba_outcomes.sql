-- fct_college_to_nba_outcomes
-- Grain: 1 row per historical prospect who reached the NBA (D-05 backbone).
--
-- Joins the college PROFILE (predictor — last season, per-40 + context +
-- trajectory) to the NBA OUTCOME (target — per-game career averages + value),
-- via int_prospect__nba_bridge. It is the base for "college profile → how it
-- panned out": fct_prospect_scouting projects a new prospect by averaging this
-- table over their comps.
--
-- Outcome = career average (D-11). Covers the 6 Bandeja de 3 categories
-- (pts/reb/ast from `draft` + stocks/3PM/TOV from stg_bbr__nba_careers via the
-- bridge, D-30) + WS/BPM/VORP. The 4 new cats can be NULL if the player's
-- career has not been scraped yet (left join in the bridge).

with bridge as (
    select *
    from {{ ref('int_prospect__nba_bridge') }}
    where n_matches = 1        -- skip ambiguous ones (manual override handled by D-09)
      and reached_nba          -- only players who actually played in the NBA
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
    -- Identity
    b.cbb_id,
    b.player_name,
    b.college_school,
    b.last_college_season,
    b.draft_year,
    b.pick,

    -- Predictor: college profile (last season)
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

    -- Target: NBA outcome (career average — D-11). The 6 Bandeja de 3 cats:
    b.nba_career_games,
    b.nba_pg_pts,
    b.nba_pg_trb,
    b.nba_pg_ast,
    b.nba_pg_stl,
    b.nba_pg_blk,
    b.nba_pg_stocks,
    b.nba_pg_fg3,
    b.nba_pg_tov,
    b.nba_win_shares,
    b.nba_bpm,
    b.nba_vorp

from bridge b
join profile pr using (cbb_id)
