-- dim_player
-- Player dimension for the current NBA season.
-- One row per player; traded players use their season-aggregate row
-- for stats, but we resolve their final team from the per-team rows.
--
-- bbr_id is the Basketball Reference player identifier (e.g. "jamesle01").
-- It is used as the stable natural key to join fct_player_game_log.

with players as (
    select * from {{ ref('int_players__deduped') }}
),

-- For traded players, find the LAST team they played for
-- (highest game count on a specific team, excluding aggregate rows).
last_team as (
    select
        player_name,
        team_abbr as last_team_abbr
    from (
        select
            player_name,
            team_abbr,
            games_played,
            row_number() over (
                partition by player_name
                order by games_played desc
            ) as rn
        from {{ ref('stg_bbr__player_stats') }}
        where team_abbr != 'TOT'
          and team_abbr !~ '^\d+TM$'
    ) ranked
    where rn = 1
),

team_info as (
    select * from {{ ref('team_info') }}
),

final as (
    select
        -- Surrogate key baseada em bbr_id (identificador estável do provedor).
        -- Nunca muda mesmo se o BBR corrigir o nome do jogador.
        {{ generate_surrogate_key(['p.bbr_id']) }}          as player_key,
        p.player_name,
        -- bbr_id: stable BBR identifier — used by fct_player_game_log
        p.bbr_id,
        p.position,
        p.age,
        coalesce(lt.last_team_abbr, p.team_abbr)           as current_team_abbr,
        ti.full_name                                        as current_team_name,
        ti.conference,
        ti.division
    from players p
    left join last_team lt
        on p.player_name = lt.player_name
        and (p.team_abbr = 'TOT' or p.team_abbr ~ '^\d+TM$')
    left join team_info ti
        on coalesce(lt.last_team_abbr, p.team_abbr) = ti.abbreviation
)

select * from final
