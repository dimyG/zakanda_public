#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals


source_names = ['xmlSoccer', 'dummy', 'test_temp_source', 'sportmonks']
default_source_name = source_names[3]
test_source_name = source_names[2]

sport_names = {
    'football': 'Football'
}

# todo xmlsoccer use names of all sources. For example in xmlsoccer the name is Bet365
# used in games/template tags and games/views
default_bookmaker_name = 'bet365'
# bookmakers that usually have similar odds and that sportmonks usually offers. It must include
# dummy in order to contain the initial odds (1.00)
mainstream_bookmakers = ['bet365', 'Coral', 'MyBet', 'Unibet', 'BetVictor', 'BWin', 'dummy']  # Bet Fred
# -----------------
# Competition Names
# -----------------

# Notice: These names are the Generic Names of competitions. They are the xmlsoccer snames. They are used by the left
# sidebar inclusion tag to get the respective competitions from the db

# the "xmlsoccer_" prefix declares the name of the competition in the xmlsoccer API
# If I prefer a different name then the preferred name is declared also along with the xmlsoccer name,
# without the xmlsoccer_ prefix

# International
international_europe_2012 = 'EURO 2012'
international_europe_2016 = 'EURO 2016'
international_europe_2020 = 'EURO 2020'

international_2012 = 'World Cup 2012'
xmlsoccer_international_2014 = 'World Cup 2014'
xmlsoccer_international_2018 = 'World Cup 2018'
xmlsoccer_international_2022 = 'World Cup 2022'

friendly_1 = 'Friendly Matches'

# Europe
xmlsoccer_europe_1 = 'Champions League'
xmlsoccer_europe_2 = 'Europe League'
europe_cup_1 = 'UEFA Super Cup'

xmlsoccer_england_1 = 'English Premier League'
xmlsoccer_england_2 = 'English League Championship'
xmlsoccer_england_3 = 'English League 1'
xmlsoccer_england_4 = 'English League 2'
xmlsoccer_england_cup_1 = 'FA Cup'
xmlsoccer_england_cup_2 = 'League Cup'
england_cup_3 = 'FA Community Shield'

xmlsoccer_spain_1 = 'La Liga'
xmlsoccer_spain_2 = 'Adelante'
spain_2 = 'Segunda Division'
spain_cup_1 = 'Copa del Rey'
spain_cup_2 = 'Spanish Super Cup'

xmlsoccer_italy_1 = 'Serie A'
xmlsoccer_italy_2 = 'Serie B'
xmlsoccer_italy_3 = 'Lega Pro'
italy_cup_1 = 'Copa Italia'
italy_cup_2 = 'Italian Super Cup'

xmlsoccer_germany_1 = 'Bundesliga'
xmlsoccer_germany_2 = '2. Bundesliga'
germany_2 = 'Bundesliga 2'
germany_cup_1 = 'DFB Pokal'
germany_cup_2 = 'German Super Cup'

xmlsoccer_france_1 = 'Ligue 1'
xmlsoccer_france_2 = 'Ligue 2'
france_cup_1 = 'Coupe de France'
france_cup_2 = 'French Super Cup'

xmlsoccer_portugal_1 = 'Primeira Liga'
portugal_2 = 'Portuguese Second Division'
portugal_cup_1 = 'Portuguese Cup'
portugal_cup_2 = 'Portuguese Super Cup'

xmlsoccer_turkey_1 = 'Süper Lig'
turkey_2 = 'Turkish Second Division'
turkey_cup_1 = 'Turkish Cup'
turkey_cup_2 = 'Turkish Super Cup'

xmlsoccer_greece_1 = 'Superleague Greece'
greece_2 = 'Football League'
greece_cup_1 = 'Greek Cup'

xmlsoccer_russia_1 = 'Russian Football Premier League'
russia_1 = 'Russian Premier League'
russia_2 = 'Russian Second Division'
russia_cup_1 = 'Russian Cup'

xmlsoccer_ukraine_1 = 'Ukrainian Premier League'
ukraine_cup_1 = 'Ukrainian Cup'

xmlsoccer_holland_1 = 'Eredivisie'
holland_2 = 'Eerste Divisie'
holland_cup_1 = 'KNVB Cup'
holland_cup_2 = 'Netherlands Super Cup'

xmlsoccer_belgium_1 = 'Jupiler League'
belgium_2 = 'Belgian Second Division'
belgium_cup_1 = 'Belgian Cup'

austria_1 = 'Austrian Bundesliga'
austria_2 = 'Austrian Second Division'
austria_cup_1 = 'Austrian Cup'

switzerland_1 = 'Swiss Super League'
switzerland_2 = 'Challenge League'
switzerland_cup_1 = 'Swiss Cup'

czech_1 = 'Czech First League'
czech_2 = 'Czech Second Division'
czech_cup_1 = 'Czech Cup'

xmlsoccer_scotland_1 = 'Scottish Premier League'
xmlsoccer_scotland_2 = 'Scottish First Division'
scotland_2 = 'Scottish Second Division'
scotland_cup_1 = 'Scottish Cup'

romania_1 = 'Liga 1'
romania_2 = 'Liga 2'
romania_cup_1 = 'Romanian Cup'

bulgaria_1 = 'A Group'
bulgaria_2 = 'B Group'
bulgaria_cup_1 = 'Bulgarian Cup'

croatia_1 = 'Croatian First League'
croatia_2 = 'Croatian Second League'
croatia_cup_1 = 'Croatian Cup'

xmlsoccer_denmark_1 = 'Superliga'
denmark_1 = 'Danish Superliga'
denmark_2 = 'Danish First Division'
denmark_cup_1 = 'Danish Cup'

xmlsoccer_sweden_1 = 'Allsvenskan'
xmlsoccer_sweden_2 = 'Superettan'
sweden_1 = 'Swedish Allsvenskan'
sweden_2 = 'Swedish Superettan'
sweden_cup_1 = 'Svenska Cupen'

xmlsoccer_norway_1 = 'Tippeligaen'
xmlsoccer_norway_2 = 'Norwegian 1. Divisjon'
norway_2 = 'Norwegian First Division'
norway_cup_1 = 'Norwegian Cup'

xmlsoccer_poland_1 = 'Ekstraklasa'
poland_2 = 'I Liga'
poland_cup_1 = 'Polish Cup'
poland_cup_2 = 'Polish SuperCup'

# America
south_america_1 = 'Copa Libertadores'
south_america_2 = 'Copa Sudamericana'

argentina_1 = 'Argentinian Premier League'
argentina_2 = 'Primera B National'
argentina_cup_1 = 'Copa Argentina'
argentina_cup_2 = 'Supercopa Argentina'

xmlsoccer_brazil_1 = 'Brasileirao'
xmlsoccer_brazil_2 = 'Brasileirão Série B'
brazil_1 = 'Campeonato Brasileiro Serie A'
brazil_2 = 'Campeonato Brasileiro Serie B'
brazil_cup_1 = 'Copa do Brasil'
brazil_cup_2 = 'Supercopa do Brasil'

xmlsoccer_mexico_1 = 'Mexican Primera League'
mexico_1 = 'Liga MX'
mexico_2 = 'Ascenso MX'
mexico_cup_1 = 'Copa MX'
mexico_cup_2 = 'Supercopa MX'

xmlsoccer_usa_1 = 'Major League Soccer'

# Asia
asia_1 = 'AFC Champions League'

uae_1 = 'Arabian Gulf League'
uae_2 = 'UAE First Division'
uae_cup_1 = 'UAE League Cup'
uae_cup_2 = 'UAE Presidents Cup'

saudi_arabia_1 = 'Saudi Professional League'
saudi_arabia_2 = 'Saudi First Division'
saudi_arabia_cup_1 = 'Saudi Crown Prince Cup'
saudi_arabia_cup_2 = 'Kings Cup'

xmlsoccer_china_1 = 'Chinese Super League'
china_2 = 'China League One'
china_cup_1 = 'Chinese FA Cup'

xmlsoccer_australia_1 = 'Australian A-League'
australia_1 = 'A League'
australia_cup_1 = 'FFA Cup'


four_year_leagues_per_season = {
    # TODO ids (or gname and country) instead of gnames
    # competition's generic name and the season that it is valid for. Notice that currently I use double
    # year seasons for these competitions
    international_europe_2012: '12/13',
    international_europe_2016: '16/17',
    xmlsoccer_international_2014: '14/15',
    # xmlsoccer_international_2018: '18/19',

    # 'EURO 2012': '2012',
    # 'EURO 2016': '2016',
    # 'World Cup 2014': '2014'
}

four_year_leagues = [
    international_europe_2012,
    international_europe_2016,
    xmlsoccer_international_2014,
    # xmlsoccer_international_2018,
]

summer_leagues = [
    # todo create competition type per season.
    # so that we know for which seasons a competition is summer and for which was winter.
    # So that in competition tree creation we apply the correct type per season
    xmlsoccer_sweden_1,
    xmlsoccer_sweden_2,
    xmlsoccer_usa_1,
    xmlsoccer_norway_1,
    xmlsoccer_norway_2,
    xmlsoccer_brazil_1,
    xmlsoccer_brazil_2,
    xmlsoccer_china_1,
]

# currently the four_year_leagues are handled as summer leagues
summer_leagues.extend(four_year_leagues)