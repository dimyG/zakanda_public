from django.contrib import admin
import models


class TeamInfoInline(admin.TabularInline):
    model = models.TeamInfo
    raw_id_fields = ('team',)
    extra = 0


class EventInfoInline(admin.TabularInline):
    model = models.EventInfo
    raw_id_fields = ('event',)
    extra = 0


# class ResultsInline(admin.TabularInline):
#     model = models.Result
#     raw_id_fields = ('event',)
#     extra = 0


class CountryInfoInline(admin.TabularInline):
    model = models.CountryInfo
    extra = 0


class CompetitionInfoInline(admin.TabularInline):
    model = models.CompetitionInfo
    extra = 0


class SeasonInfoInline(admin.TabularInline):
    model = models.SeasonInfo
    raw_id_fields = ('season',)
    extra = 0


class CompetitionSeasonInline(admin.TabularInline):
    model = models.CompetitionSeason
    raw_id_fields = ('season', 'competition', 'infos')
    extra = 0


class WinnerOfferOddInline(admin.TabularInline):
    model = models.WinnerOfferOdd
    raw_id_fields = ('odd', 'offer', 'bookmaker')
    extra = 0


class DoubleChanceOfferOddInline(admin.TabularInline):
    model = models.DoubleChanceOfferOdd
    raw_id_fields = ('odd', 'offer', 'bookmaker')
    extra = 0


class OverUnderOfferOddInline(admin.TabularInline):
    model = models.OverUnderOfferOdd
    raw_id_fields = ('odd', 'offer', 'bookmaker')
    extra = 0


class HandicapOfferOddInline(admin.TabularInline):
    model = models.HandicapOfferOdd
    raw_id_fields = ('odd', 'offer', 'bookmaker')
    extra = 0


@admin.register(models.Source)
class SourceAdmin(admin.ModelAdmin):
    # inlines = (TeamInfoInline, EventInfoInline)
    pass


@admin.register(models.Country)
class CountryAdmin(admin.ModelAdmin):
    inlines = (CountryInfoInline,)
    search_fields = ('name', '=id')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(models.CountryInfo)
class CountryInfoAdmin(admin.ModelAdmin):
    search_fields = ('sname', '=sid')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(models.Event)
class EventAdmin(admin.ModelAdmin):
    inlines = (EventInfoInline,)
    raw_id_fields = ('competition_season', 'home_team', 'away_team')
    search_fields = ('^home_team__generic_name', '^away_team__generic_name', '=id',
                     '^competition_season__competition__generic_name', '^competition_season__season__name',
                     '^competition_season__competition__country__name')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(models.EventInfo)
class EventInfoAdmin(admin.ModelAdmin):
    raw_id_fields = ('event',)
    search_fields = ('^event__home_team__generic_name', '^event__away_team__generic_name', '=id', '=sid')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(models.Result)
class ResultAdmin(admin.ModelAdmin):
    search_fields = ('=id',)
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(models.TeamInfo)
class TeamAdmin(admin.ModelAdmin):
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('team',)
    search_fields = ['^sname', '^team__generic_name', '=id', '=sid']


@admin.register(models.Team)
class TeamAdmin(admin.ModelAdmin):
    inlines = (TeamInfoInline,)
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('competition_seasons',)
    search_fields = ['^generic_name', '=id']


@admin.register(models.SeasonInfo)
class SeasonInfoAdmin(admin.ModelAdmin):
    raw_id_fields = ('season',)
    search_fields = ['^sname', '=sid']
    readonly_fields = ('id', )


@admin.register(models.Season)
class SeasonAdmin(admin.ModelAdmin):
    inlines = (SeasonInfoInline,)
    search_fields = ['^name', '=id']
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(models.Competition)
class CompetitionAdmin(admin.ModelAdmin):
    inlines = (CompetitionInfoInline, CompetitionSeasonInline,)
    raw_id_fields = ('country',)
    search_fields = ['^generic_name', 'country__name', '=id']
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(models.CompetitionInfo)
class CompetitionInfoAdmin(admin.ModelAdmin):
    raw_id_fields = ('competition',)
    search_fields = ['^sgname', '^competition__generic_name', 'competition__country__name', '=id']
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(models.CompetitionSeason)
class CompetitionSeasonAdmin(admin.ModelAdmin):
    raw_id_fields = ('season', 'competition', 'infos')
    search_fields = ['^competition__generic_name', 'competition__country__name', '=id']
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(models.CompetitionSeasonInfo)
class CompetitionSeasonInfoAdmin(admin.ModelAdmin):
    search_fields = ['^sname', '=id', '=sid']
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(models.BetEvent)
class BetEventAdmin(admin.ModelAdmin):
    # date_hierarchy = 'date'
    # filter_horizontal = ''
    raw_id_fields = ('event', 'selection')
    search_fields = ('^event__home_team__generic_name', '^event__away_team__generic_name', '=id')
    readonly_fields = ('id', 'created_at', 'updated_at')


# Winner Offer
@admin.register(models.WinnerOffer)
class WinnerOfferAdmin(admin.ModelAdmin):
    inlines = (WinnerOfferOddInline,)
    raw_id_fields = ('event',)
    search_fields = ('^event__home_team__generic_name', '^event__away_team__generic_name', '=id')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(models.WinnerOfferOdd)
class WinnerOfferOddAdmin(admin.ModelAdmin):
    raw_id_fields = ('odd', 'offer', 'bookmaker')
    search_fields = ('^bookmaker__name', '=odd__home', '=odd__away', '=odd__draw', '=id',
                     '^offer__event__home_team__generic_name', '^offer__event__away_team__generic_name')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(models.WinnerOdd)
class WinnerOddAdmin(admin.ModelAdmin):
    search_fields = ('=home', '=away', '=draw', '=id')
    readonly_fields = ('id', 'created_at', 'updated_at')


# Double Chance Offer
@admin.register(models.DoubleChanceOffer)
class DoubleChanceOfferAdmin(admin.ModelAdmin):
    inlines = (DoubleChanceOfferOddInline,)
    raw_id_fields = ('event',)
    search_fields = ('^event__home_team__generic_name', '^event__away_team__generic_name', '=id')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(models.DoubleChanceOfferOdd)
class DoubleChanceOfferOddAdmin(admin.ModelAdmin):
    raw_id_fields = ('odd', 'offer', 'bookmaker')
    search_fields = ('^bookmaker__name', '=odd__home_draw', '=odd__draw_away',
                     '=odd__away_home', '=id', '^offer__event__home_team__generic_name',
                     '^offer__event__away_team__generic_name')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(models.DoubleChanceOdd)
class DoubleChanceOddAdmin(admin.ModelAdmin):
    search_fields = ('=home_draw', '=draw_away', '=away_home', '=id')
    readonly_fields = ('id', 'created_at', 'updated_at')


# Over Under Offer
@admin.register(models.OverUnderOffer)
class OverUnderOfferAdmin(admin.ModelAdmin):
    inlines = (OverUnderOfferOddInline,)
    raw_id_fields = ('event',)
    search_fields = ('^event__home_team__generic_name', '^event__away_team__generic_name', '=threshold', '=id')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(models.OverUnderOfferOdd)
class OverUnderOfferOddAdmin(admin.ModelAdmin):
    raw_id_fields = ('odd', 'offer', 'bookmaker')
    search_fields = ('^bookmaker__name', '=odd__over', '=odd__under',
                     '=offer__threshold', '=id', '^offer__event__home_team__generic_name',
                     '^offer__event__away_team__generic_name')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(models.OverUnderOdd)
class OverUnderOddAdmin(admin.ModelAdmin):
    search_fields = ('=over', '=under', '=id')
    readonly_fields = ('id', 'created_at', 'updated_at')


# Handicap Offer
@admin.register(models.HandicapOffer)
class HandicapOfferAdmin(admin.ModelAdmin):
    inlines = (HandicapOfferOddInline,)
    raw_id_fields = ('event',)
    search_fields = ('^event__home_team__generic_name', '^event__away_team__generic_name', '=threshold', '=id')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(models.HandicapOfferOdd)
class HandicapOfferOddAdmin(admin.ModelAdmin):
    raw_id_fields = ('odd', 'offer', 'bookmaker')
    search_fields = ('^bookmaker__name', '=odd__home', '=odd__away', '=odd__draw',
                     '=offer__threshold', '=id', '^offer__event__home_team__generic_name',
                     '^offer__event__away_team__generic_name')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(models.HandicapOdd)
class HandicapOddAdmin(admin.ModelAdmin):
    search_fields = ('=home', '=draw', '=away')
    readonly_fields = ('id', 'created_at', 'updated_at')


admin.site.register(models.Sport)
admin.site.register(models.SportInfo)

admin.site.register(models.Bookmaker)
admin.site.register(models.BookmakerInfo)

admin.site.register(models.MarketType)
admin.site.register(models.MarketResult)

admin.site.register(models.AsianHandicapOdd)
admin.site.register(models.AsianHandicapOffer)
admin.site.register(models.AsianHandicapOfferOdd)

admin.site.register(models.Selection)

admin.site.register(models.Bet)
admin.site.register(models.TotalBet)
