-- dim_team
-- Team dimension combining static reference data (team_info seed)
-- with current-era franchise stats from BBR.
--
-- BBR's teams page lists all historical franchise eras as separate rows.
-- Multiple eras can share the same franchise_name and all have
-- season_to = '2025-26' (BBR marks them all as still active).
-- We use ROW_NUMBER() to keep only the row with the MOST GAMES PLAYED
-- for each franchise, which represents the full all-time historical record.

with team_info as (
    select * from {{ ref('team_info') }}
),

team_stats_raw as (
    select *
    from {{ ref('stg_bbr__teams') }}
    where season_to = '2025-26'
),

-- Pick the all-time record row (most games = longest franchise era)
team_stats as (
    select *
    from (
        select
            *,
            row_number() over (
                partition by franchise_name
                order by games_played desc
            ) as rn
        from team_stats_raw
    ) ranked
    where rn = 1
),

final as (
    select
        {{ generate_id(['ti.abbreviation']) }}               as team_key,
        ti.abbreviation                                     as team_abbr,
        ti.full_name                                        as team_name,
        ti.city,
        ti.conference,
        ti.division,
        ts.wins,
        ts.losses,
        ts.win_loss_pct,
        ts.playoff_appearances,
        ts.division_titles,
        ts.conference_titles,
        ts.championships
    from team_info ti
    left join team_stats ts
        on ti.full_name = ts.franchise_name
)

select * from final
