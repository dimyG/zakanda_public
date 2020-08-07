# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
from django.conf import settings
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('bet_tagging', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AsianHandicapOdd',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('home', models.FloatField(validators=[django.core.validators.MinValueValidator(1)])),
                ('away', models.FloatField(validators=[django.core.validators.MinValueValidator(1)])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='AsianHandicapOffer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('threshold_1', models.FloatField()),
                ('threshold_2', models.FloatField(default=None, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='AsianHandicapOfferOdd',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('asian_handicap_odd', models.ForeignKey(to='games.AsianHandicapOdd')),
                ('asian_handicap_offer', models.ForeignKey(to='games.AsianHandicapOffer')),
            ],
            options={
                'get_latest_by': 'timestamp',
            },
        ),
        migrations.CreateModel(
            name='Bet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('amount', models.FloatField()),
                ('odd', models.FloatField(default=None, null=True)),
                ('bet_return', models.FloatField(default=None, null=True)),
                ('status', models.CharField(default='Open', max_length=5, choices=[('Won', 'Won'), ('Lost', 'Lost'), ('Open', 'Open')])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='BetEvent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Bookmaker',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=30)),
                ('url', models.URLField(default=None, unique=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='BookmakerInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('sid', models.IntegerField(default=None, null=True)),
                ('sname', models.CharField(max_length=30)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('bookmaker', models.ForeignKey(to='games.Bookmaker')),
            ],
            options={
                'get_latest_by': 'created_at',
            },
        ),
        migrations.CreateModel(
            name='Competition',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('generic_name', models.CharField(max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='CompetitionInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('sid', models.PositiveIntegerField()),
                ('sgname', models.CharField(default=None, max_length=50, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('competition', models.ForeignKey(to='games.Competition')),
            ],
            options={
                'get_latest_by': 'created_at',
            },
        ),
        migrations.CreateModel(
            name='CompetitionSeason',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(default='Winter', max_length=6, choices=[('Winter', 'Winter'), ('Summer', 'Summer')])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('competition', models.ForeignKey(related_name='competition_seasons', to='games.Competition')),
            ],
            options={
                'get_latest_by': 'created_at',
            },
        ),
        migrations.CreateModel(
            name='CompetitionSeasonInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('sid', models.PositiveIntegerField(default=None, null=True)),
                ('sname', models.CharField(max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'get_latest_by': 'created_at',
            },
        ),
        migrations.CreateModel(
            name='Country',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=30)),
                ('fifa_code', models.CharField(default=None, max_length=30, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='CountryInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('sid', models.IntegerField(default=None, null=True)),
                ('sname', models.CharField(max_length=30)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('country', models.ForeignKey(to='games.Country')),
            ],
            options={
                'get_latest_by': 'created_at',
            },
        ),
        migrations.CreateModel(
            name='DoubleChanceOdd',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('home_draw', models.FloatField(validators=[django.core.validators.MinValueValidator(1)])),
                ('draw_away', models.FloatField(validators=[django.core.validators.MinValueValidator(1)])),
                ('away_home', models.FloatField(validators=[django.core.validators.MinValueValidator(1)])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='DoubleChanceOffer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='DoubleChanceOfferOdd',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('bookmaker', models.ForeignKey(related_name='bookmaker_doublechanceofferodds_set', to='games.Bookmaker')),
                ('double_chance_odd', models.ForeignKey(to='games.DoubleChanceOdd')),
                ('double_chance_offer', models.ForeignKey(to='games.DoubleChanceOffer')),
            ],
            options={
                'get_latest_by': 'timestamp',
            },
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(verbose_name='Event date')),
                ('round', models.PositiveIntegerField(default=None, null=True)),
                ('status', models.CharField(default='Not Started', max_length=35, choices=[('Not Started', 'Not Started'), ('Finished', 'Finished'), ('Finished AET', 'Finished AET (Added Extra Time)'), ('Finished AP', 'Finished AP (Added Penalty)'), ('Cancelled', 'Cancelled'), ('Postponed', 'Postponed'), ('Abandoned', 'Abandoned'), ('in_play', 'in_play')])),
                ('live', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['date'],
                'get_latest_by': 'date',
            },
        ),
        migrations.CreateModel(
            name='EventInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('sid', models.PositiveIntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('event', models.ForeignKey(related_name='event_infos', to='games.Event')),
            ],
            options={
                'get_latest_by': 'created_at',
            },
        ),
        migrations.CreateModel(
            name='FinalScoreResult',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('result', models.CharField(default=None, max_length=10, null=True, choices=[('1-0', '1-0'), ('2-0', '2-0'), ('2-1', '2-1'), ('3-0', '3-0'), ('3-1', '3-1'), ('3-2', '3-2'), ('4-0', '4-0'), ('4-1', '4-1'), ('4-2', '4-2'), ('4-3', '4-3'), ('5-0', '5-0'), ('5-1', '5-1'), ('5-2', '5-2'), ('5-3', '5-3'), ('6-0', '6-0'), ('6-1', '6-1'), ('6-2', '6-2'), ('7-0', '7-0'), ('7-1', '7-1'), ('0-0', '0-0'), ('1-1', '1-1'), ('2-2', '2-2'), ('3-3', '3-3'), ('0-1', '0-1'), ('0-2', '0-2'), ('1-2', '1-2'), ('0-3', '0-3'), ('1-3', '1-3'), ('2-3', '2-3'), ('0-4', '0-4'), ('1-4', '1-4'), ('2-4', '2-4'), ('3-4', '3-4'), (None, 'Open')])),
            ],
        ),
        migrations.CreateModel(
            name='HandicapOdd',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('home', models.FloatField(validators=[django.core.validators.MinValueValidator(1)])),
                ('draw', models.FloatField(validators=[django.core.validators.MinValueValidator(1)])),
                ('away', models.FloatField(validators=[django.core.validators.MinValueValidator(1)])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='HandicapOffer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('threshold', models.FloatField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('event', models.ForeignKey(related_name='event_handicapoffers_set', to='games.Event')),
            ],
        ),
        migrations.CreateModel(
            name='HandicapOfferOdd',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('bookmaker', models.ForeignKey(related_name='bookmaker_handicapofferodds_set', to='games.Bookmaker')),
                ('handicap_odd', models.ForeignKey(to='games.HandicapOdd')),
                ('handicap_offer', models.ForeignKey(to='games.HandicapOffer')),
            ],
            options={
                'get_latest_by': 'timestamp',
            },
        ),
        migrations.CreateModel(
            name='MarketResult',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('result', models.CharField(default='Open', max_length=15, unique=True, null=True, choices=[('Open', 'Open'), ('Void', 'Void'), ('1', '1'), ('X', 'X'), ('2', '2'), ('1', '1'), ('X', 'X'), ('2', '2'), ('Over', 'Over'), ('Under', 'Under'), ('1X', '1X'), ('X2', 'X2'), ('12', '12')])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='MarketType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=30, choices=[('Full Time Result', 'Full Time Result'), ('Goals Over Under 2.5', 'Goals Over Under 2.5'), ('Double chance', 'Double chance'), ('Handicap 1-0', 'Handicap 1-0'), ('Handicap 2-0', 'Handicap 2-0'), ('Handicap 3-0', 'Handicap 3-0'), ('Handicap 0-1', 'Handicap 0-1'), ('Handicap 0-2', 'Handicap 0-2'), ('Handicap 0-3', 'Handicap 0-3'), ('Asian Handicap +0.5', 'Asian Handicap +0.5'), ('Asian Handicap +1.5', 'Asian Handicap +1.5'), ('Asian Handicap +2.5', 'Asian Handicap +2.5'), ('Asian Handicap 0', 'Asian Handicap 0'), ('Asian Handicap +1', 'Asian Handicap +1'), ('Asian Handicap +2', 'Asian Handicap +2'), ('Asian Handicap -0.5', 'Asian Handicap -0.5'), ('Asian Handicap -1.5', 'Asian Handicap -1.5'), ('Asian Handicap -2.5', 'Asian Handicap -2.5'), ('Asian Handicap -1', 'Asian Handicap -1'), ('Asian Handicap -2', 'Asian Handicap -2'), ('Asian Handicap 0,+0.5', 'Asian Handicap 0,+0.5'), ('Asian Handicap +0.5,+1', 'Asian Handicap +0.5,+1'), ('Asian Handicap +1,+1.5', 'Asian Handicap +1,+1.5'), ('Asian Handicap +1.5,+2', 'Asian Handicap +1.5,+2'), ('Asian Handicap +2,+2.5', 'Asian Handicap +2,+2.5'), ('Asian Handicap 0,-0.5', 'Asian Handicap 0,-0.5'), ('Asian Handicap -0.5,-1', 'Asian Handicap -0.5,-1'), ('Asian Handicap -1,-1.5', 'Asian Handicap -1,-1.5'), ('Asian Handicap -1.5,-2', 'Asian Handicap -1.5,-2'), ('Asian Handicap -2,-2.5', 'Asian Handicap -2,-2.5')])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('asian_handicap_offers', models.ManyToManyField(to='games.AsianHandicapOffer')),
                ('double_chance_offers', models.ManyToManyField(to='games.DoubleChanceOffer')),
                ('handicap_offers', models.ManyToManyField(to='games.HandicapOffer')),
            ],
        ),
        migrations.CreateModel(
            name='OverUnderOdd',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('over', models.FloatField(validators=[django.core.validators.MinValueValidator(1)])),
                ('under', models.FloatField(validators=[django.core.validators.MinValueValidator(1)])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='OverUnderOffer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('threshold', models.FloatField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('event', models.ForeignKey(related_name='event_overunderoffers_set', to='games.Event')),
                ('market_result', models.ForeignKey(related_name='marketresult_overunderoffers_set', to='games.MarketResult')),
            ],
        ),
        migrations.CreateModel(
            name='OverUnderOfferOdd',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('bookmaker', models.ForeignKey(related_name='bookmaker_overunderofferodds_set', to='games.Bookmaker')),
                ('over_under_odd', models.ForeignKey(to='games.OverUnderOdd')),
                ('over_under_offer', models.ForeignKey(to='games.OverUnderOffer')),
            ],
            options={
                'get_latest_by': 'timestamp',
            },
        ),
        migrations.CreateModel(
            name='Result',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('home_goals', models.PositiveIntegerField()),
                ('away_goals', models.PositiveIntegerField()),
                ('minute', models.PositiveIntegerField()),
                ('extra_minute', models.PositiveIntegerField(default=0)),
                ('type', models.CharField(default='IN_PLAY', max_length=15, choices=[('IN_PLAY', 'IN_PLAY'), ('HT', 'HT'), ('FT', 'FT'), ('ET_HT', 'ET_HT'), ('ET', 'ET'), ('PEN', 'PEN'), ('Postponed', 'Postponed'), ('Cancelled', 'Cancelled'), ('Abandoned', 'Abandoned'), ('Interrupted', 'Interrupted'), ('Suspended', 'Suspended')])),
                ('final', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Season',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=5, choices=[('1983', '1983'), ('1984', '1984'), ('1985', '1985'), ('1986', '1986'), ('1987', '1987'), ('1988', '1988'), ('1989', '1989'), ('1990', '1990'), ('1991', '1991'), ('1992', '1992'), ('1993', '1993'), ('1994', '1994'), ('1995', '1995'), ('1996', '1996'), ('1997', '1997'), ('1998', '1998'), ('1999', '1999'), ('2000', '2000'), ('2001', '2001'), ('2002', '2002'), ('2003', '2003'), ('2004', '2004'), ('2005', '2005'), ('2006', '2006'), ('2007', '2007'), ('2008', '2008'), ('2009', '2009'), ('2010', '2010'), ('2011', '2011'), ('2012', '2012'), ('2013', '2013'), ('2014', '2014'), ('2015', '2015'), ('2016', '2016'), ('2017', '2017'), ('2018', '2018'), ('2019', '2019'), ('2020', '2020'), ('2021', '2021'), ('2022', '2022'), ('2023', '2023'), ('2024', '2024'), ('2025', '2025'), ('2026', '2026'), ('2027', '2027'), ('2028', '2028'), ('2029', '2029'), ('2030', '2030'), ('93/94', '93/94'), ('94/95', '94/95'), ('95/96', '95/96'), ('96/97', '96/97'), ('97/98', '97/98'), ('98/99', '98/99'), ('99/00', '99/00'), ('00/01', '00/01'), ('01/02', '01/02'), ('02/03', '02/03'), ('03/04', '03/04'), ('04/05', '04/05'), ('05/06', '05/06'), ('06/07', '06/07'), ('07/08', '07/08'), ('08/09', '08/09'), ('09/10', '09/10'), ('10/11', '10/11'), ('11/12', '11/12'), ('12/13', '12/13'), ('13/14', '13/14'), ('14/15', '14/15'), ('15/16', '15/16'), ('16/17', '16/17'), ('17/18', '17/18'), ('18/19', '18/19'), ('19/20', '19/20'), ('20/21', '20/21'), ('21/22', '21/22'), ('22/23', '22/23'), ('23/24', '23/24'), ('24/25', '24/25'), ('25/26', '25/26'), ('26/27', '26/27'), ('27/28', '27/28'), ('28/29', '28/29'), ('29/30', '29/30')])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='SeasonInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('sid', models.IntegerField()),
                ('sname', models.CharField(max_length=10)),
                ('season', models.ForeignKey(to='games.Season')),
            ],
        ),
        migrations.CreateModel(
            name='Selection',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('original_odd', models.FloatField()),
                ('selected_odd', models.FloatField()),
                ('choice', models.CharField(max_length=15, choices=[('1', '1'), ('X', 'X'), ('2', '2'), ('Over', 'Over'), ('Under', 'Under'), ('1', '1'), ('X', 'X'), ('2', '2'), ('Over', 'Over'), ('Under', 'Under'), ('1X', '1X'), ('X2', 'X2'), ('12', '12')])),
                ('status', models.CharField(default='Open', max_length=5, choices=[('Won', 'Won'), ('Lost', 'Lost'), ('Open', 'Open'), ('Void', 'Void')])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Source',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Sport',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=30)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='SportInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('sid', models.IntegerField(default=None, null=True)),
                ('sname', models.CharField(max_length=30)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('source', models.ForeignKey(to='games.Source')),
                ('sport', models.ForeignKey(to='games.Sport')),
            ],
            options={
                'get_latest_by': 'created_at',
            },
        ),
        migrations.CreateModel(
            name='Team',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('generic_name', models.CharField(unique=True, max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('competition_seasons', models.ManyToManyField(to='games.CompetitionSeason')),
            ],
        ),
        migrations.CreateModel(
            name='TeamInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('sid', models.PositiveIntegerField()),
                ('sname', models.CharField(max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('source', models.ForeignKey(related_name='team_infos', to='games.Source')),
                ('team', models.ForeignKey(to='games.Team')),
            ],
            options={
                'get_latest_by': 'created_at',
            },
        ),
        migrations.CreateModel(
            name='TotalBet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(default='default', max_length=30)),
                ('date', models.DateTimeField(verbose_name='Bet date')),
                ('decision_date', models.DateTimeField(default=None, null=True)),
                ('amount', models.FloatField()),
                ('odd', models.FloatField(default=None, null=True)),
                ('total_return', models.FloatField(default=None, null=True)),
                ('status', models.CharField(default='Open', max_length=5, choices=[('Won', 'Won'), ('Lost', 'Lost'), ('Open', 'Open')])),
                ('bet_tag_balance_snapshot', models.FloatField()),
                ('description', models.CharField(default=None, max_length=1500, null=True)),
                ('url', models.URLField(default=None, null=True)),
                ('public', models.BooleanField(default=True)),
                ('is_past', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('bet_tag', models.ForeignKey(related_name='total_bets', to='bet_tagging.BetTag')),
                ('bets', models.ManyToManyField(to='games.Bet')),
                ('bookmaker', models.ForeignKey(related_name='total_bets', to='games.Bookmaker')),
                ('user', models.ForeignKey(related_name='total_bets', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='WinnerOdd',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('home', models.FloatField(validators=[django.core.validators.MinValueValidator(1)])),
                ('draw', models.FloatField(validators=[django.core.validators.MinValueValidator(1)])),
                ('away', models.FloatField(validators=[django.core.validators.MinValueValidator(1)])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='WinnerOffer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('event', models.OneToOneField(to='games.Event')),
                ('market_result', models.ForeignKey(related_name='marketresult_winneroffers_set', to='games.MarketResult')),
            ],
        ),
        migrations.CreateModel(
            name='WinnerOfferOdd',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('bookmaker', models.ForeignKey(related_name='bookmaker_winnerofferodds_set', to='games.Bookmaker')),
                ('source', models.ForeignKey(related_name='source_winnerofferodds_set', to='games.Source')),
                ('winner_odd', models.ForeignKey(to='games.WinnerOdd')),
                ('winner_offer', models.ForeignKey(to='games.WinnerOffer')),
            ],
            options={
                'get_latest_by': 'timestamp',
            },
        ),
        migrations.AddField(
            model_name='winneroffer',
            name='winner_odds',
            field=models.ManyToManyField(to='games.WinnerOdd', through='games.WinnerOfferOdd'),
        ),
        migrations.AlterUniqueTogether(
            name='winnerodd',
            unique_together=set([('home', 'draw', 'away')]),
        ),
        migrations.AddField(
            model_name='team',
            name='sources',
            field=models.ManyToManyField(related_name='teams', through='games.TeamInfo', to='games.Source'),
        ),
        migrations.AddField(
            model_name='sport',
            name='sources',
            field=models.ManyToManyField(related_name='sports', through='games.SportInfo', to='games.Source'),
        ),
        migrations.AlterUniqueTogether(
            name='selection',
            unique_together=set([('original_odd', 'selected_odd', 'choice', 'status')]),
        ),
        migrations.AddField(
            model_name='seasoninfo',
            name='source',
            field=models.ForeignKey(to='games.Source'),
        ),
        migrations.AddField(
            model_name='season',
            name='sources',
            field=models.ManyToManyField(related_name='seasons', through='games.SeasonInfo', to='games.Source'),
        ),
        migrations.AddField(
            model_name='overunderofferodd',
            name='source',
            field=models.ForeignKey(related_name='source_overunderofferodds_set', to='games.Source'),
        ),
        migrations.AddField(
            model_name='overunderoffer',
            name='over_under_odds',
            field=models.ManyToManyField(to='games.OverUnderOdd', through='games.OverUnderOfferOdd'),
        ),
        migrations.AlterUniqueTogether(
            name='overunderodd',
            unique_together=set([('over', 'under')]),
        ),
        migrations.AddField(
            model_name='markettype',
            name='over_under_offers',
            field=models.ManyToManyField(to='games.OverUnderOffer'),
        ),
        migrations.AddField(
            model_name='markettype',
            name='winner_offers',
            field=models.ManyToManyField(to='games.WinnerOffer'),
        ),
        migrations.AddField(
            model_name='handicapofferodd',
            name='source',
            field=models.ForeignKey(related_name='source_handicapofferodds_set', to='games.Source'),
        ),
        migrations.AddField(
            model_name='handicapoffer',
            name='handicap_odds',
            field=models.ManyToManyField(to='games.HandicapOdd', through='games.HandicapOfferOdd'),
        ),
        migrations.AddField(
            model_name='handicapoffer',
            name='market_result',
            field=models.ForeignKey(related_name='marketresult_handicapoffers_set', to='games.MarketResult'),
        ),
        migrations.AlterUniqueTogether(
            name='handicapodd',
            unique_together=set([('home', 'draw', 'away')]),
        ),
        migrations.AddField(
            model_name='eventinfo',
            name='source',
            field=models.ForeignKey(related_name='source_eventinfos_set', to='games.Source'),
        ),
        migrations.AddField(
            model_name='event',
            name='away_team',
            field=models.ForeignKey(related_name='as_away_team_events_set', to='games.Team'),
        ),
        migrations.AddField(
            model_name='event',
            name='competition_season',
            field=models.ForeignKey(related_name='competitionseason_events_set', to='games.CompetitionSeason'),
        ),
        migrations.AddField(
            model_name='event',
            name='home_team',
            field=models.ForeignKey(related_name='as_home_team_events_set', to='games.Team'),
        ),
        migrations.AddField(
            model_name='event',
            name='market_types',
            field=models.ManyToManyField(to='games.MarketType'),
        ),
        migrations.AddField(
            model_name='event',
            name='results',
            field=models.ManyToManyField(to='games.Result', blank=True),
        ),
        migrations.AddField(
            model_name='event',
            name='sources',
            field=models.ManyToManyField(to='games.Source', through='games.EventInfo'),
        ),
        migrations.AddField(
            model_name='doublechanceofferodd',
            name='source',
            field=models.ForeignKey(related_name='source_doublechanceofferodds_set', to='games.Source'),
        ),
        migrations.AddField(
            model_name='doublechanceoffer',
            name='double_chance_odds',
            field=models.ManyToManyField(to='games.DoubleChanceOdd', through='games.DoubleChanceOfferOdd'),
        ),
        migrations.AddField(
            model_name='doublechanceoffer',
            name='event',
            field=models.OneToOneField(to='games.Event'),
        ),
        migrations.AddField(
            model_name='doublechanceoffer',
            name='market_result',
            field=models.ForeignKey(related_name='marketresult_doublechanceoffers_set', to='games.MarketResult'),
        ),
        migrations.AlterUniqueTogether(
            name='doublechanceodd',
            unique_together=set([('home_draw', 'draw_away', 'away_home')]),
        ),
        migrations.AddField(
            model_name='countryinfo',
            name='source',
            field=models.ForeignKey(to='games.Source'),
        ),
        migrations.AddField(
            model_name='country',
            name='sources',
            field=models.ManyToManyField(related_name='countries', through='games.CountryInfo', to='games.Source'),
        ),
        migrations.AddField(
            model_name='competitionseasoninfo',
            name='source',
            field=models.ForeignKey(to='games.Source'),
        ),
        migrations.AddField(
            model_name='competitionseason',
            name='infos',
            field=models.ManyToManyField(related_name='competition_seasons', to='games.CompetitionSeasonInfo'),
        ),
        migrations.AddField(
            model_name='competitionseason',
            name='season',
            field=models.ForeignKey(related_name='competition_seasons', to='games.Season'),
        ),
        migrations.AddField(
            model_name='competitioninfo',
            name='source',
            field=models.ForeignKey(to='games.Source'),
        ),
        migrations.AddField(
            model_name='competition',
            name='country',
            field=models.ForeignKey(related_name='country_competitions_set', to='games.Country'),
        ),
        migrations.AddField(
            model_name='competition',
            name='seasons',
            field=models.ManyToManyField(related_name='competitions', through='games.CompetitionSeason', to='games.Season'),
        ),
        migrations.AddField(
            model_name='competition',
            name='sources',
            field=models.ManyToManyField(related_name='competitions', through='games.CompetitionInfo', to='games.Source'),
        ),
        migrations.AddField(
            model_name='competition',
            name='sport',
            field=models.ForeignKey(related_name='sport_competitions_set', to='games.Sport'),
        ),
        migrations.AddField(
            model_name='bookmakerinfo',
            name='source',
            field=models.ForeignKey(to='games.Source'),
        ),
        migrations.AddField(
            model_name='bookmaker',
            name='sources',
            field=models.ManyToManyField(related_name='bookmakers', through='games.BookmakerInfo', to='games.Source'),
        ),
        migrations.AddField(
            model_name='betevent',
            name='event',
            field=models.ForeignKey(related_name='bet_events', to='games.Event'),
        ),
        migrations.AddField(
            model_name='betevent',
            name='market_type',
            field=models.ForeignKey(related_name='markettype_betevent_set', to='games.MarketType'),
        ),
        migrations.AddField(
            model_name='betevent',
            name='selection',
            field=models.ForeignKey(related_name='selection_betevent_set', to='games.Selection'),
        ),
        migrations.AddField(
            model_name='bet',
            name='bet_events',
            field=models.ManyToManyField(to='games.BetEvent'),
        ),
        migrations.AddField(
            model_name='asianhandicapofferodd',
            name='bookmaker',
            field=models.ForeignKey(related_name='bookmaker_asianhandicapofferodds_set', to='games.Bookmaker'),
        ),
        migrations.AddField(
            model_name='asianhandicapofferodd',
            name='source',
            field=models.ForeignKey(related_name='source_asianhandicapofferodds_set', to='games.Source'),
        ),
        migrations.AddField(
            model_name='asianhandicapoffer',
            name='asian_handicap_odds',
            field=models.ManyToManyField(to='games.AsianHandicapOdd', through='games.AsianHandicapOfferOdd'),
        ),
        migrations.AddField(
            model_name='asianhandicapoffer',
            name='event',
            field=models.ForeignKey(related_name='event_asianhandicapoffers_set', to='games.Event'),
        ),
        migrations.AddField(
            model_name='asianhandicapoffer',
            name='market_result',
            field=models.ForeignKey(related_name='marketresult_asianhandicapoffers_set', to='games.MarketResult'),
        ),
        migrations.AlterUniqueTogether(
            name='asianhandicapodd',
            unique_together=set([('home', 'away')]),
        ),
        migrations.AlterUniqueTogether(
            name='winnerofferodd',
            unique_together=set([('winner_odd', 'winner_offer', 'bookmaker', 'source', 'timestamp')]),
        ),
        migrations.AlterUniqueTogether(
            name='teaminfo',
            unique_together=set([('source', 'sid', 'sname')]),
        ),
        migrations.AlterUniqueTogether(
            name='sportinfo',
            unique_together=set([('source', 'sid', 'sname')]),
        ),
        migrations.AlterUniqueTogether(
            name='seasoninfo',
            unique_together=set([('source', 'sid', 'sname')]),
        ),
        migrations.AlterUniqueTogether(
            name='overunderofferodd',
            unique_together=set([('over_under_odd', 'over_under_offer', 'bookmaker', 'source', 'timestamp')]),
        ),
        migrations.AlterUniqueTogether(
            name='overunderoffer',
            unique_together=set([('event', 'threshold')]),
        ),
        migrations.AlterUniqueTogether(
            name='handicapofferodd',
            unique_together=set([('handicap_odd', 'handicap_offer', 'bookmaker', 'source', 'timestamp')]),
        ),
        migrations.AlterUniqueTogether(
            name='handicapoffer',
            unique_together=set([('event', 'threshold')]),
        ),
        migrations.AlterUniqueTogether(
            name='eventinfo',
            unique_together=set([('source', 'sid', 'event')]),
        ),
        migrations.AlterUniqueTogether(
            name='doublechanceofferodd',
            unique_together=set([('double_chance_odd', 'double_chance_offer', 'bookmaker', 'source', 'timestamp')]),
        ),
        migrations.AlterUniqueTogether(
            name='countryinfo',
            unique_together=set([('source', 'sid', 'sname')]),
        ),
        migrations.AlterUniqueTogether(
            name='competitionseasoninfo',
            unique_together=set([('source', 'sname', 'sid')]),
        ),
        migrations.AlterUniqueTogether(
            name='competitionseason',
            unique_together=set([('competition', 'season')]),
        ),
        migrations.AlterUniqueTogether(
            name='competitioninfo',
            unique_together=set([('source', 'sid')]),
        ),
        migrations.AlterUniqueTogether(
            name='competition',
            unique_together=set([('country', 'sport', 'generic_name')]),
        ),
        migrations.AlterUniqueTogether(
            name='bookmakerinfo',
            unique_together=set([('source', 'sid', 'sname')]),
        ),
        migrations.AlterUniqueTogether(
            name='asianhandicapofferodd',
            unique_together=set([('asian_handicap_odd', 'asian_handicap_offer', 'bookmaker', 'source', 'timestamp')]),
        ),
        migrations.AlterUniqueTogether(
            name='asianhandicapoffer',
            unique_together=set([('event', 'threshold_1', 'threshold_2')]),
        ),
    ]
