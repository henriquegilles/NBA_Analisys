-- int_prospect__nba_bridge
-- Grain: 1 row per college prospect matched to a draft pick.
--
-- College→NBA bridge (D-09): matches the prospect (most recent college season)
-- to their NBA career in the `draft` seed, which already carries per-game CAREER
-- averages (pg_pts/trb/ast) + value (WS/BPM/VORP) — exactly the "career average"
-- outcome of D-11, for those categories.
--
-- Matching is by normalized NAME + a draft-year WINDOW (±1 from the end of the
-- last college season), which disambiguates namesakes from different eras (e.g.
-- Corliss Williamson 1995 vs. Zion Williamson 2019). When the window is NOT
-- enough (namesakes from adjacent years, e.g. Justin Jackson UNC 2017 vs.
-- Maryland 2018), the manual seed `college_nba_id_overrides` (D-09) pins the
-- canonical NBA slug. `n_matches` is recomputed AFTER the override — past that
-- point it should always be 1.
--
-- Full 6 categories (D-30): pts/trb/ast come from `draft`; stl/blk (→stocks),
-- 3PM and TOV come from stg_bbr__nba_careers ("Career" row of the player page),
-- joined on the NBA slug `nba_bbr_id`. The join is LEFT: a prospect whose career
-- has not been scraped yet gets the 4 new cats as NULL (the row is not lost).

with prospect_latest as (
    select cbb_id, player_name, school, season,
           left(season, 4)::int + 1 as season_end_year
    from (
        select *, row_number() over (partition by cbb_id order by season desc) as rn
        from {{ ref('int_prospect__college_stats') }}
    ) s
    where rn = 1
),

draft as (
    select
        trim("player_name"::text)                          as player_name,
        nullif(trim("bbr_id"::text), '')                   as nba_bbr_id,
        nullif(trim("college"::text), '')                  as nba_college,
        nullif(trim("draft_year"::text), '')::int          as draft_year,
        nullif(trim("pick"::text), '')::int                as pick,
        nullif(trim("pg_pts"::text), '')::numeric(5,1)     as nba_pg_pts,
        nullif(trim("pg_trb"::text), '')::numeric(5,1)     as nba_pg_trb,
        nullif(trim("pg_ast"::text), '')::numeric(5,1)     as nba_pg_ast,
        nullif(trim("career_games"::text), '')::int        as nba_career_games,
        nullif(trim("win_shares"::text), '')::numeric(6,1) as nba_win_shares,
        nullif(trim("bpm"::text), '')::numeric(6,1)        as nba_bpm,
        nullif(trim("vorp"::text), '')::numeric(6,1)       as nba_vorp
    from {{ ref('draft') }}
    where trim("player_name"::text) <> ''
      and nullif(trim("draft_year"::text), '') is not null
),

-- Full 6-cat NBA career (the stl/blk/3PM/TOV that `draft` does not carry).
-- Joined on the NBA slug — canonical key, no namesake ambiguity (D-30).
careers as (
    select bbr_id, pg_stl, pg_blk, pg_fg3, pg_tov
    from {{ ref('stg_bbr__nba_careers') }}
),

matched as (
    select
        p.cbb_id,
        p.player_name,
        p.school                                           as college_school,
        p.season                                           as last_college_season,
        d.nba_bbr_id,
        d.nba_college,
        d.draft_year,
        d.pick,
        (d.nba_pg_pts is not null)                         as reached_nba,
        d.nba_pg_pts, d.nba_pg_trb, d.nba_pg_ast,
        -- Full 6-cat: stl/blk/3PM/TOV from the NBA career (left join — NULL if
        -- the career has not been scraped yet). stocks = stl + blk.
        c.nba_pg_stl, c.nba_pg_blk, c.nba_pg_stocks, c.nba_pg_fg3, c.nba_pg_tov,
        d.nba_career_games, d.nba_win_shares, d.nba_bpm, d.nba_vorp
    from prospect_latest p
    join draft d
      on lower(trim(p.player_name)) = lower(trim(d.player_name))
     and d.draft_year between p.season_end_year - 1 and p.season_end_year + 1
    left join (
        select
            bbr_id,
            pg_stl                 as nba_pg_stl,
            pg_blk                 as nba_pg_blk,
            (pg_stl + pg_blk)      as nba_pg_stocks,
            pg_fg3                 as nba_pg_fg3,
            pg_tov                 as nba_pg_tov
        from careers
    ) c on c.bbr_id = d.nba_bbr_id
),

-- D-09: manual identity fixes for namesakes the year window cannot
-- disambiguate. Maps the prospect's cbb_id to the canonical NBA slug; with
-- that we discard the wrong matches for the same prospect.
overrides as (
    select
        nullif(trim("cbb_id"::text), '')     as cbb_id,
        nullif(trim("nba_bbr_id"::text), '') as nba_bbr_id
    from {{ ref('college_nba_id_overrides') }}
),

resolved as (
    select m.*
    from matched m
    left join overrides o on o.cbb_id = m.cbb_id
    where o.cbb_id is null               -- no override: keep all matches
       or m.nba_bbr_id = o.nba_bbr_id     -- with override: only the canonical NBA slug
)

-- n_matches recomputed AFTER the override (should be 1 for everyone now).
select
    *,
    count(*) over (partition by cbb_id) as n_matches
from resolved
