from __future__ import unicode_literals
import logging
import sys
import itertools
from collections import defaultdict
from django.core.exceptions import FieldError
import zakanda.db
import games.models
import games.naming
from gutils import markets_creation


logger = logging.getLogger(__name__)


def get_football():
    try:
        football = games.models.Sport.objects.get(name=games.naming.sport_names['football'])
    except Exception as e:
        logger.warning('%s Probably the database has no zakanda schema or no data yet', e)
        football = None
    return football


# These Pre models hold the data from the APIs. The API responses have different attributes and
# structure with each other. No matter what the structure and attributes are, data is stored
# in these common Pre models. The way that the API data is saved in the database is common
# no matter which API we use. These Pre models are also common and they "know" how to save
# tha data to the database. So all API's data is transformed to this common format and then
# saved easily to the database.

# Mapping must be done only if entities read from a new source are going to be created.
# If you just re-read entities from an existing source then internal mapping is required
# and it is performed by default no matter the mapping boolean value.

def define_entity():
    # input methods are functions so that they can easily overridden with another input method
    # and also easily tested with functions that return a specific value
    return raw_input('Your input is required...'
                     '1: Type 1 if this entity exists in the db '
                     '2: Type 2 if this entity does not exist in the db and needs to be created '
                     '0: Type 0 to stop editing and exit the function '
                     'For any other input, the entity_tree will not be created')


def define_id():
    return raw_input("Type the id of the existing entity")


class MappedEntity(object):

    @classmethod
    def describe(cls, pre_models):
        """ The pre models must have been passed through the mapping process """
        logger.info("analyzing given pre models...")
        if not pre_models:
            return None, None, None
        existing_entities = []
        new_entities = []
        to_be_remapped_entities = []
        invalids = []
        for obj in pre_models:
            if not obj.is_valid():  # validity must be checked first so that the object isn't processed as a new entity
                invalids.append(obj)
                continue
            if not obj.exists:
                new_entities.append(obj)
            elif obj.exists and obj.existing_entity:
                existing_entities.append(obj)
            else:
                to_be_remapped_entities.append(obj)

        new_num = len(new_entities)
        exist_num = len(existing_entities)
        remap_num = len(to_be_remapped_entities)
        invalids_num = len(invalids)
        logger.info('%s entities were read', len(pre_models))
        logger.info('New entities: %s, Existing entities: %s, To be remapped entities: %s, Invalid entities: %s', new_num, exist_num, remap_num, invalids_num)
        if remap_num:
            logger.warning('IMPORTANT: The mapping process must be rerun for the remaining %s entities', remap_num)
        return new_entities, existing_entities, to_be_remapped_entities

    @classmethod
    def exhaustive_unmapped_mapping(cls, pre_models):
        """ It checks if there are some pre entities that need to be remapped and runs
        them through the mapping process. It repeats that until all entities are successfully mapped """
        if not pre_models:
            return [], [], []
        new_ents, existing_ents, to_remap_ents = cls.describe(pre_models)
        while to_remap_ents:
            logger.info('Some pre entities haven not been saved in db. Define them properly now...')
            for pre_ent in to_remap_ents:
                pre_ent.get_or_create()
            new_ents, existing_ents, to_remap_ents = NameMappedEntity.describe(pre_models)
        return new_ents, existing_ents, to_remap_ents


class NameMappedEntity(MappedEntity):
    # the base entity has a common generic name and each source might use different names

    # todo have in mind the case in which the data source changes the data for a specific entity (different sid, name etc)
    # if there is an integrity error when you create the entity then it means that something from the same
    # source has changed and the existing entity info must be updated

    # todo as proof of validity we can run a check for each group and compare its length with the supposed
    # one. For example check if the number of teams in a competition is the one that is supposed to be
    def __init__(self, source, sname, sid, exists=False, existing_entity=None):
        self.source = source  # a source object
        self.sname = sname
        self.sid = sid
        self.exists = exists
        self.existing_entity = existing_entity
        self.model = None

    @classmethod
    def validity_irrelevent_args(cls):
        # these arguments don't influence an object's validity
        return ['exists', 'existing_entity']

    def identify(self, define_entity_fun=define_entity, define_id_fun=define_id):
        model = self.model
        logger.warning('Manual action is required for the %s entity: %s with sid: %s from source: %s',
                       model, self.sname, self.sid, self.source)
        entity_exists = define_entity_fun()
        if entity_exists == "1":
            # case 3
            existing_id = define_id_fun()
            try:
                # case 3a
                entity = model.objects.get(id=existing_id)
                self.existing_entity = entity
            except Exception as e:
                # case 3b
                logger.warning('%s, given id %s does not correspond to an existing %s entity', e, existing_id, model)
            self.exists = True
        elif entity_exists == "2":
            pass  # case 1
        elif entity_exists == '0':
            sys.exit()  # raises the SystemExit exception in the current thread
        else:
            self.exists = True  # user input error is handled as 3b, existing_entity = None
        return

    def map(self, mapping=True, define_entity_fun=define_entity, define_id_fun=define_id):
        """
        Possible combinations of values: exist/existing_entity
        - False/Anything: New entity
        - True/NotNone: Entity exists and has either the same name with the processed entity or a different one
        - True/None: The entity exists but the user didn't defined which is the existing entity.
                    In this case the map must be rerun so that the user defines the existing entity

        An Example in case in which model = games.models.Country
        The country for the specific source name
        1. does not exist in the db (will pass from get_or_create)
        2. an entity with the same name exist in the db (the read entity corresponds to this existing entity since the
           name is unique) (will pass from get_or_create)
        3. exists in the db with a different name
            a. user gives the existing country's id and this id is valid (will pass from get_or_create)
            b. user gives an invalid country id
                This case is represented with self.exists = True and self.existing_entity = None
               (will not pass from get_or_create, so country info for this will not be created.
               The function should be called again and the user must give a valid id)
        :param mapping: In case of empty database there is no need for mapping
        """

        if not mapping:
            return  # skip the mapping process
        if not self.model:
            logger.warning('Can not map a raw MappedEntity object!')
            return

        sname = self.sname
        model = self.model
        try:
            # case 2
            try:
                entity = model.objects.get(name=sname)
            except FieldError:
                entity = model.objects.get(generic_name=sname)
            self.exists = True
            self.existing_entity = entity
            return

        except model.DoesNotExist:
            self.identify(define_entity_fun=define_entity_fun, define_id_fun=define_id_fun)
        return

    def get_gname(self):
        if not self.exists:
            # the country will be created for the first time and its gname will be the sname
            # of the source that creates this country for the first time
            return self.sname
        else:
            if self.existing_entity:
                try:
                    gname = self.existing_entity.name
                except AttributeError:
                    gname = self.existing_entity.generic_name
                return gname


class ManuallyMappedEntity(NameMappedEntity):
    def __init__(self, source, sname, sid, exists=False, existing_entity=None):
        super(ManuallyMappedEntity, self).__init__(source, sname, sid, exists, existing_entity)

    def map(self, mapping=True, define_entity_fun=define_entity, define_id_fun=define_id):
        """ These entities have no unique gname. For example you can have many Competitions named Premier League.
        So we can't identify an existing entity by it's name. In this case user input is required for every entity """
        if not mapping:
            return  # skip the mapping process
        if not self.model:
            logger.warning('Can not map a raw MappedEntity object!')
            return
        self.identify(define_entity_fun=define_entity_fun, define_id_fun=define_id_fun)
        return


class PreCountry(NameMappedEntity):
    def __init__(self, source, sname, sid, fifa_code=None, flag=None):
        super(PreCountry, self).__init__(source, sname, sid)
        self.model = games.models.Country
        self.fifa_code = fifa_code
        self.flag = flag

    def __unicode__(self):
        return "{} {} {}".format(self.source, self.sname, self.sid)

    def is_valid(self):
        if not self.source or not self.sname or not self.sid:
            logger.warning("Invalid PreCountry object %s", self)
            return False
        return True

    def map(self, mapping=True, define_entity_fun=define_entity, define_id_fun=define_id):
        """ First we check if the country exists for the same source. If not, then if it exists for any source """
        # internal_map must always run, even if there are no teams in the db
        self.internal_map()
        if not self.existing_entity:
            # if an entity has been identified (self.existing_entity exists) then no further action is required.
            # But if the processed entity is a new one for this given source, we must check if it refers to an
            # existing team of a different source.
            super(PreCountry, self).map(mapping=mapping, define_entity_fun=define_entity_fun, define_id_fun=define_id_fun)

    def internal_map(self):
        # Notice: If there is a new sname and different sid for an existing country there is no way to identify
        # this existing country only with the sname and sid. You also need something else like long, lat
        # fifa code etc. Currently a new country will be created for it and the leagues that are included
        # to it will be assigned to this country (since in pre competitions the competitions are updated
        # with a new country if necessary). So there will be some countries, the old ones, that will be without
        # any competition. These empty countries do not appear in the sports list
        try:
            existing_entity = self.model.by_sid(self.sid, self.source)
            if not existing_entity:
                # if sname is the same then there is an sid change in the source
                existing_entity = self.model.by_sname(self.sname, self.source)
            if existing_entity:
                self.exists = True
                self.existing_entity = existing_entity
        except Exception as e:
            pass

    def get_or_create(self, mapping=True, define_entity_fun=define_entity, define_id_fun=define_id):
        self.map(mapping, define_entity_fun, define_id_fun)
        country_gname = self.get_gname()
        if not country_gname:
            logger.warning('preCountry tree %s was not get or created, probably invalid id was given', self)
            return None, None
        country, country_info = zakanda.db.create_country_tree(country_gname, self.source, self.sname, self.sid, self.fifa_code)
        return country, country_info

    def get(self):
        try:
            country = games.models.CountryInfo.objects.get(source=self.source, sid=self.sid, sname=self.sname).country
        except Exception as e:
            logger.warning('%s - pre_country: %s', e, self)
            country = None
        return country


class CompetitionSeasonUtil:
    """ It holds some help data for the creation of the competition_season_tree. I use this class instead of
    dictionaries that map the seasons to specific sids and snames. One such object is created for each
    read competition. The competition is not yet created/get so its not available """
    def __init__(self, season, competition_season_sid, competition_season_sname, competition_season_type):
        self.season = season  # season object
        self.competition_season_sid = competition_season_sid  # competition_season_specific sid
        self.competition_season_sname = competition_season_sname  # competition_season_specific sname
        self.competition_season_type = competition_season_type

    def __unicode__(self):
        return "{} {} {}".format(self.competition_season_sname, self.season, self.competition_season_sid)

    def is_valid(self):
        if not self.season or not self.competition_season_sid or not self.competition_season_sname:
            logger.warning("Invalid CompetitionSeasonUtil object %s", self)
            return False
        return True


class PreCompetition(ManuallyMappedEntity):
    """ You can run it many times for the same source without the need to perform mapping.
    If all attributes are the same then no new entity will be created """
    def __init__(self, source, sname, sid, sport_name, competition_season_utils, pre_country):
        super(PreCompetition, self).__init__(source, sname, sid)
        self.model = games.models.Competition
        self.sport_name = sport_name
        self.competition_season_utils = competition_season_utils  # list of CompetitionSeasonUtil objects
        self.pre_country = pre_country  # PreCountry object

    def __unicode__(self):
        return "{} {} {}".format(self.sname, self.sid, self.source)

    def is_valid(self):
        if not self.source or not self.sname or not self.sid or not self.sport_name \
                or not self.competition_season_utils or not self.pre_country:
            logger.warning("Invalid PreCompetition object %s", self)
            return False
        try:
            valid_utils = []
            for util in self.competition_season_utils:
                if util.is_valid():
                    valid_utils.append(util)
            if not valid_utils:  # if all the utils are invalid
                return False
        except Exception:  # util is not a Util object and has no is_valid method
            return False
        return True

    def get_sport(self):
        sport_name = self.sport_name
        try:
            sport = games.models.Sport.objects.get(name=sport_name)
        except Exception as e:
            logger.warning("%s: given sport name was %s", e, sport_name)
            sport = None
        return sport

    def map(self, mapping=True, define_entity_fun=define_entity, define_id_fun=define_id):
        """ First we check if the competition exists for the same source. If not, then if it exists for any source """
        # internal_map must always run, even if there are no teams in the db
        self.internal_map()
        if not self.existing_entity:
            # if an entity has been identified (self.existing_entity exists) then no further action is required.
            # But if the processed team is a new team for this given source, we must check if it refers to an
            # existing team of a different source.
            super(PreCompetition, self).map(mapping=mapping, define_entity_fun=define_entity_fun, define_id_fun=define_id_fun)

    def internal_map(self):
        """ An entry already exists if it has the given sid and source """
        source = self.source
        competition_sid = self.sid
        existing_competition = games.models.Competition.by_sid(competition_sid, source)
        if not existing_competition:
            return
        self.exists = True
        self.existing_entity = existing_competition

    def to_be_updated(self, country, sport):
        existing_entity = self.existing_entity
        if not existing_entity:
            return False
        if country == existing_entity.country and existing_entity.sport == sport:
            return False
        return True

    def info_to_be_updated(self, sgname):
        existing_entity = self.existing_entity
        if not existing_entity:
            return False
        existing_sgname = self.get_existing_sgname()
        if sgname == existing_sgname:
            return False
        return True

    def update_if_needed(self, country, sport, sgname):
        """ If the processed pre_competition refers to an existing competition, but the
        country or the sport (mainly the country) that the source gives, is different from the country
        of the existing competition, it means that it was to the existing country by mistake (of the source).
        So the existing competition is updated with the new country. In this case, the get_or_create will
        not create a new competition. It will just get the updated existing one. If a new competition was created
        then an Integrity error would be raised in the competition info creation since the same info entry
        could not refer to more than one competitions (the old wrong one and the new one)
        The same applies to sgname too, only that in this case the competition_info is updated.
        :param country: The country that was extracted from the source data
        :param sport: The sport that was extracted from the source data
        :param sgname: The sgname extracted from the source data
        :return:
        """
        if not country or not sport or not sgname:
            return False
        updated = False
        if self.to_be_updated(country, sport):
            existing_entity = self.existing_entity
            logger.info("existing entity %s is updated with new country %s (old: %s) and sport %s (old: %s), "
                        "[source %s]", existing_entity, country, existing_entity.country,
                        sport, existing_entity.sport, self.source)
            existing_entity.country = country
            existing_entity.sport = sport
            existing_entity.save()
            updated = True
        if self.info_to_be_updated(sgname):
            existing_info = self.get_competition_info()
            logger.info("existing competition info %s is updated with new sgname %s (old: %s), [source %s]",
                        existing_info, sgname, self.get_existing_sgname(), self.source)
            existing_info.sgname = sgname
            existing_info.save()
            updated = True
        return updated

    # def get_sgname(self):
    #     # Not used: It was prefered to update the existing sgname if there is a new one
    #     # If a competition exists then the existing sgname will be used. If not then it will be
    #     # the same with the gname.
    #     sgname = self.get_gname()
    #     if self.existing_entity:
    #         try:
    #             sgname = games.models.CompetitionInfo.objects.get(
    #                 competition=self.existing_entity, sid=self.sid, source=self.source).sgname
    #         except Exception as e:
    #             logger.warning('%s', e)
    #     return sgname

    def get_competition_info(self):
        return games.models.CompetitionInfo.get_competition_info(self.source, self.sid)

    def get_existing_sgname(self):
        competition_info = self.get_competition_info()
        if not competition_info:
            return
        return competition_info.sgname

    def get_or_create(self, mapping=True, define_entity_fun=define_entity, define_id_fun=define_id):
        """
        For clarity countries must be already created so that this call only creates competitions
        :return:
        """
        if not self.is_valid():
            return None, None
        self.map(mapping, define_entity_fun, define_id_fun)
        # country, sport and gname (the attributes that uniquely define a competition) must take their
        # value from the existing entity if this exists
        country = self.pre_country.get()  # countries must be already created
        sport = self.get_sport()
        updated = self.update_if_needed(country, sport, self.sname)
        if not country or not sport:
            logger.warning('%s will not be get_or_created', self)
            return None, None
        competition_gname = self.get_gname()
        # sgname = self.get_sgname()
        if not competition_gname:
            logger.warning('preCompetition tree %s was not get or created, probably invalid id was given', self)
            return None, None
        competition, competition_seasons = zakanda.db.create_competition_tree(
            # have in mind that in case of sgname change the existing competition_info is updated
            # but the existing competition_season_infos remain the same and new entries are created with the new name.
            # You could choose the other option, which is to update the proper competition_season_info objects if
            # but it's not necessary
            competition_season_utils=self.competition_season_utils, competition_gname=competition_gname, country=country,
            sport=sport, source=self.source, competition_sgname=self.sname, competition_sid=self.sid
        )
        return competition, competition_seasons


class PreTeam(ManuallyMappedEntity):
    def __init__(self, source, sname, sid, sport_name, competition_season):
        super(PreTeam, self).__init__(source, sname, sid)
        self.model = games.models.Team
        self.sport_name = sport_name
        self.competition_season = competition_season  # a competition_season object in which the team will be connected

    def __unicode__(self):
        return "{} {} {}".format(self.sname, self.sid, self.source)

    def map(self, mapping=True, define_entity_fun=define_entity, define_id_fun=define_id):
        """ First we check if the team exists for the same source. If not, then if it exists for any source """
        # internal_map must always run, even if there are no teams in the db
        self.internal_map()
        if not self.existing_entity:
            # if an entity has been identified (self.existing_entity exists) then no further action is required.
            # But if the processed team is a new team for this given source, we must check if it refers to an
            # existing team of a different source.
            super(PreTeam, self).map(mapping=mapping, define_entity_fun=define_entity_fun, define_id_fun=define_id_fun)

    def make_new_name(self):
        delimiter = "__#"
        sname = self.sname
        split = sname.split(delimiter)
        if len(split) == 1:
            counter = 1
            new_name = sname + delimiter + str(counter)
        elif len(split) == 2:
            try:
                counter = int(split[1])
            except ValueError:
                counter = 1000
            counter += 1
            new_name = split[0] + delimiter + str(counter)
        else:
            logger.warning("Wrong use of same name delimiter for sname %s", sname)
            new_name = sname + delimiter  # just to make it a new name
        logger.info("sname: %s changed to: %s for pre_team %s", sname, new_name, self)
        return new_name

    def internal_map(self):
        """ The original mapping was created to handle the mapping of entities between sources since
        we assumed that an entity from the same source has a unique characteristic (for example unique name)
        But this is not the case for teams. This function handles the mapping of pre_entities of the same source

        The combination of source, sname and sid uniquely identifies a team. So we check if there
        is a team in the db with the same source, sname and sid. If it does then the processed pre team
        refers to the existing team. If there is a team from the same source with the same sname but a
        different sid, then the processed team is a new team despite the fact that it has the same sname.
        Since we require unique team gnames, we change the sname of the processed team

        Notice: In case of name update it updates the existing team generic name
        """
        if not self.model:
            logger.warning('Can not map a raw MappedEntity object!')
            return
        source = self.source
        if not isinstance(self.source, games.models.Source):
            logger.warning("%s is not a source object", self.source)
            return
        original_sname = self.sname
        sid = self.sid
        model = self.model

        same_source_teams = self.source.teams.all()
        if not same_source_teams:
            return
        same_named_teams = same_source_teams.filter(team_infos__sname=original_sname)
        if same_named_teams:
            # if a team has 2 team_infos this query will return the same team twice
            team = same_named_teams.filter(team_infos__sid=sid).first()
            self.exists = True
            self.existing_entity = team
            if not team:
                # a team from the same source with the same sname already exists in the db,
                # but it has a different sid. This means that they are different teams and the new team
                # will be saved with a new sname and gname
                # todo NOW the source changed the sid for a team and kept the same sname. I must handle this case.
                # it could be identified by comparing the  competition_season of this team with the competition_seasons
                # of the existing same named team. If they have a common comp_seas it's an indication that is the
                # same team
                self.sname = self.make_new_name()
                self.internal_map()  # check the new name
        else:
            try:
                same_sid_team = same_source_teams.filter(team_infos__sid=sid).first()
                if same_sid_team:
                    # The source has a new name for an existing team (Probably there was a rebranding of the team)
                    logger.warning("New sname %s [%s] for team with sid %s. A new info will be added "
                                   "to the team. (It's gname will remain the same)", self.sname, source, sid)
                    # the generic name is the old name so it should be updated to be the new one
                    # same_sid_team.generic_name = self.sname  # better not mess with the global name
                    # same_sid_team.save()
                    self.exists = True
                    self.existing_entity = same_sid_team
            except Exception as e:
                logger.warning('unexpected error: %s', e)
                return

    def is_valid(self):
        checked_args = self.__dict__.copy()
        for arg in self.validity_irrelevent_args():
            checked_args.pop(arg)
        values = checked_args.values()
        # logger.info('validating %s, for args: %s', self, values)
        for arg in values:
            if not arg:
                logger.warning("Invalid PreTeam object %s", self)
                return False
        return True

    # todo high remove teams from competition_seasons that are not connected with anymore, according to the source
    # they were initially connected by a previous call that contained wrong data.

    def get_or_create(self, mapping=True, define_entity_fun=define_entity, define_id_fun=define_id):
        if not self.is_valid():
            logger.warning("%s is Invalid", self)
            return
        self.map(mapping, define_entity_fun, define_id_fun)
        team_gname = self.get_gname()
        # Actually all the attributes that define an entity must take their value from the existing entity
        # if this exists. Here the only attribute that defines a team is the gname (it is unique in zakanda)
        if not team_gname:
            logger.warning('preTeam tree %s was not get or created, probably invalid id was given', self)
            return
        team, team_created, team_info, team_info_created = zakanda.db.create_team_tree(
            gname=team_gname, source=self.source, sname=self.sname, sid=self.sid,
            competition_season=self.competition_season)
        return team

    @classmethod
    def get_distinct(cls, pre_teams):
        """ The given pre_teams must be of the same source. If the sid is the same then it is the same team.
        Notice that this must not be used to filter the pre_teams before their creation since each team
        belongs to a different competition_season and we want to be connected with that by the create team tree """
        if not pre_teams:
            return pre_teams
        distinct = dict()
        for pre_team in pre_teams:
            distinct[pre_team.sid] = pre_team
        return distinct.values()

    @classmethod
    def by_name(cls, pre_teams):
        """ returns a dictionary in which key is the fetched team name and value is the sids that use this name
        It is used to identify teams with the same name """
        by_name_dict = defaultdict(list)
        for pre_team in pre_teams:
            by_name_dict[pre_team.name].append(pre_team.id)
        return by_name_dict

    @classmethod
    def get_same_named(cls, pre_teams):
        """ returns a dictionary of the pre_teams that have the same sname. The key is the fetched team name
        and value is the sids that use this name"""
        by_name = cls.by_name(pre_teams)
        same_name_dict = by_name.copy()
        for name, sids in by_name.iteritems():
            if len(sids) <= 1:
                same_name_dict.pop(name)
        if same_name_dict:
            logger.warning("Teams with the same name: %s. Action might be necessary!", same_name_dict)
        return same_name_dict


class PreEvent(object):
    def __init__(self, source, sid, utc_date, home_team, away_team, competition_season, event_round=None, event=None):
        # it gets teams and comp_season objects instead of names or sids since each source returns different
        # attributes like sname or sid. I could add snames and sids and get the objects from them
        self.source = source
        self.sid = sid
        self.utc_date = utc_date
        self.home_team = home_team  # object
        self.away_team = away_team  # object
        self.competition_season = competition_season  # object
        self.round = event_round
        self.event = event  # the event that is created from self realization

    def __unicode__(self):
        return "{} - {} {} {} {} {}".format(self.home_team, self.away_team, self.competition_season, self.utc_date, self.sid, self.round)

    def are_teams_in_competition_season(self):
        home_team = self.home_team
        away_team = self.away_team
        competition_season = self.competition_season
        try:
            source_name = self.source.name
        except Exception as e:
            source_name = None
        if not home_team or not away_team or not competition_season:
            return False
        belong_list = []
        for team in [home_team, away_team]:
            if competition_season not in team.competition_seasons.all():
                team_sids = team.get_sids(source_name)
                competition_season_sids = competition_season.get_sids(source_name)
                logger.error("Team %s [%s %s] doesn't belong to competition_season %s [%s %s]. Event %s", team, source_name,
                             team_sids, competition_season, source_name, competition_season_sids, self)
                belong_list.append(False)
            else:
                belong_list.append(True)
        if False in belong_list:
            return False
        return True

    def is_valid(self):
        if not self.home_team or not self.away_team or not self.competition_season or not self.utc_date \
                or not self.source or not self.sid or not self.are_teams_in_competition_season():
            # event_round can be empty
            logger.warning("Invalid PreEvent object %s", self)
            return False
        return True

    def get_or_create(self):
        if not self.is_valid():
            return None, None
        event, event_created, event_info, event_info_created = zakanda.db.create_event_tree(
            self.utc_date, self.competition_season, self.home_team, self.away_team, self.round, self.source, self.sid
        )
        self.event = event
        if not event:
            logger.error('no event was created for the valid pre_event %s', self)
            return event, event_info
        if event.status not in games.models.Event.open_event_statuses:
            # The case that this solves:
            # There is an event that is postponed for a later date. When the new one is created
            # the old one is marked as postponed and the new one is of open status. But if
            # you make a call to get the fixtures of previous dates then the old event will be returned again
            # from the data source, and upon it's pre model's creation process, it's brothers will be settled.
            # But one of its brothers is the new event that will be marked as postponed. We don't want that so
            # we avoid this by checking if the event that is going to be created is open. If it is not
            # then this means that it is an old event that has already pass through this creation process
            # and it's brothers must not be settled since the new valid event exists among them.
            logger.info("event %s is not open so it's brothers will not be settled", event)
            return event, event_info
        # this call is for the case that the brothers haven't been already settled by a call to get their result.
        event.settle_brothers(source=self.source)  # todo collect all brothers and settle them afterwards
        return event, event_info


class PreOdd(object):
    def __init__(self, event_sid, source, bookmaker_name, bookmaker_sid, timestamp, fetched_market_name):
        self.event_sid = event_sid
        self.source = source
        self.bookmaker_name = bookmaker_name
        self.bookmaker_sid = bookmaker_sid
        self.timestamp = timestamp  # utc aware
        self.fetched_market_name = fetched_market_name  # the market type name as read from the source

    @classmethod
    def validity_irrelevent_args(cls):
        return ['bookmaker_sid']

    def odds(self):
        return

    def odds_valid(self):
        """ checks if odds exist, can become float, are not the initial odds, have no 2 equal values """
        odds = self.odds()
        if not odds:
            return False

        try:
            odds = [float(odd) for odd in odds]
        except Exception:
            return False

        set_odds = set(odds)
        if len(set_odds) == 1 and list(set_odds)[0] == 1:
            # if all odds are 1 it is the initial odd and is considered valid
            return True

        for odd1, odd2 in itertools.combinations(odds, 2):
            # creates all possible combinations by 2
            # odds like [1]1.01 [X]2.5 [2]1.01 are not valid
            if odd1 - odd2 == 0:
                return False
        return True

    def is_valid(self):
        checked_args = self.__dict__.copy()
        for arg in self.validity_irrelevent_args():
            checked_args.pop(arg)
        args = checked_args.values()
        # logger.info('validating %s, for args: %s', self, args)
        for arg in args:
            try:
                arg = float(arg)
            except Exception:
                pass
            if not arg:
                logger.warning("Invalid PreOdd object %s", self)
                return False
        if not self.odds_valid():
            return False
        return True

    def event(self):
        event = games.models.Event.latest_event_from_sid(self.event_sid, self.source)
        return event

    def __unicode__(self):
        return "{} {}".format(self.event_sid, self.bookmaker_name)


class PreWinnerOdd(PreOdd):
    def __init__(self, event_sid, source, bookmaker_name, bookmaker_sid, timestamp, fetched_market_name, home, draw, away):
        super(PreWinnerOdd, self).__init__(event_sid, source, bookmaker_name, bookmaker_sid, timestamp, fetched_market_name)
        self.home = home
        self.draw = draw
        self.away = away

    @classmethod
    def market_name(cls):
        return games.models.MarketType.winner_market_type

    def odds(self):
        return [self.home, self.draw, self.away]

    def to_numbers(self):
        try:
            self.home = float(self.home)
            self.draw = float(self.draw)
            self.away = float(self.away)
        except Exception as e:
            return

    def get_or_create(self):
        event = self.event()
        if not self.is_valid() or not event:
            return None, None, None, None
        self.to_numbers()
        winner_odd, winner_offer, winner_offer_odd, tree_created = markets_creation.create_winner_offer_tree(
            event, self.bookmaker_name, self.bookmaker_sid, self.timestamp, self.home, self.draw, self.away, self.source)
        return winner_odd, winner_offer, winner_offer_odd, tree_created


class PreOverUnderOdd(PreOdd):
    def __init__(self, event_sid, source, bookmaker_name, bookmaker_sid, timestamp, fetched_market_name, over, under, threshold):
        super(PreOverUnderOdd, self).__init__(event_sid, source, bookmaker_name, bookmaker_sid, timestamp, fetched_market_name)
        self.over = over
        self.under = under
        self.threshold = threshold

    def market_name(self):
        threshold = self.threshold
        market_name = games.models.MarketType.get_name(threshold, None, games.models.MarketType.generic_goals_ovun)
        return market_name

    def odds(self):
        return [self.over, self.under]

    def to_numbers(self):
        try:
            self.threshold = float(self.threshold)
            self.over = float(self.over)
            self.under = float(self.under)
        except Exception as e:
            return

    def get_or_create(self):
        event = self.event()
        if not self.is_valid() or not event:
            return None, None, None, None
        self.to_numbers()
        over_under_odd, over_under_offer, over_under_offer_odd, tree_created = markets_creation.create_overunder_offer_tree(
            event, self.bookmaker_name, self.bookmaker_sid, self.timestamp, self.over, self.under, self.threshold, self.source)
        return over_under_odd, over_under_offer, over_under_offer_odd, tree_created


class PreDoubleChanceOdd(PreOdd):
    def __init__(self, event_sid, source, bookmaker_name, bookmaker_sid, timestamp, fetched_market_name, home_draw, draw_away, away_home):
        super(PreDoubleChanceOdd, self).__init__(event_sid, source, bookmaker_name, bookmaker_sid, timestamp, fetched_market_name)
        self.home_draw = home_draw
        self.draw_away = draw_away
        self.away_home = away_home

    def market_name(self):
        return games.models.MarketType.double_chance_market_type

    def odds(self):
        return [self.home_draw, self.draw_away, self.away_home]

    def to_numbers(self):
        try:
            self.home_draw = float(self.home_draw)
            self.draw_away = float(self.draw_away)
            self.away_home = float(self.away_home)
        except Exception as e:
            return

    def get_or_create(self):
        event = self.event()
        if not self.is_valid() or not event:
            return None, None, None, None
        self.to_numbers()
        double_chance_odd, double_chance_offer, double_chance_offer_odd, tree_created = markets_creation.create_double_chance_offer_tree(
            event, self.bookmaker_name, self.bookmaker_sid, self.timestamp, self.home_draw, self.draw_away, self.away_home, self.source)
        return double_chance_odd, double_chance_offer, double_chance_offer_odd, tree_created


class PreHandicapOdd(PreOdd):
    def __init__(self, event_sid, source, bookmaker_name, bookmaker_sid, timestamp, fetched_market_name, home, draw, away, threshold):
        super(PreHandicapOdd, self).__init__(event_sid, source, bookmaker_name, bookmaker_sid, timestamp, fetched_market_name)
        self.home = home
        self.draw = draw
        self.away = away
        self.threshold = threshold

    def market_name(self):
        threshold = self.threshold
        market_name = games.models.MarketType.get_name(threshold, None, games.models.MarketType.generic_handicap)
        return market_name

    def odds(self):
        return [self.home, self.draw, self.away]

    def to_numbers(self):
        try:
            self.threshold = float(self.threshold)
            self.home = float(self.home)
            self.draw = float(self.draw)
            self.away = float(self.away)
        except Exception as e:
            return

    def get_or_create(self):
        event = self.event()
        # logger.debug('PreHandicap data: %s, %s, %s, %s', event, self.bookmaker_name, self.threshold, self.odds())
        if not self.is_valid() or not event:
            return None, None, None, None
        self.to_numbers()
        handicap_odd, handicap_offer, handicap_offer_odd, tree_created = markets_creation.create_handicap_offer_tree(
            event, self.bookmaker_name, self.bookmaker_sid, self.timestamp, self.home, self.draw, self.away,
            self.threshold, self.source)
        return handicap_odd, handicap_offer, handicap_offer_odd, tree_created


class PreUnsupported(PreOdd):
    def __init__(self, event_sid, source, bookmaker_name, bookmaker_sid, timestamp, fetched_market_name):
        super(PreUnsupported, self).__init__(event_sid, source, bookmaker_name, bookmaker_sid, timestamp, fetched_market_name)

    def get_or_create(self):
        return


class PreResult(object):
    def __init__(self, event, fetched_status, home_goals, away_goals, result_type, minute, is_final, source, sport=get_football):
        if not isinstance(sport, games.models.Sport):
            sport = sport()
        self.event = event
        self.source = source
        self.fetched_event_status = fetched_status  # the fetched status is not necessary for creating the pre_result
        self.home_goals = home_goals  # int
        self.away_goals = away_goals
        self.result_type = result_type
        self.minute = minute  # int
        self.is_final = is_final
        self.sport = sport

    def __unicode__(self):
        return "{} {} {} {}".format(self.fetched_event_status, self.home_goals, self.away_goals, self.is_final)

    def is_valid(self):
        args = self.__dict__.values()
        # logger.info('validating %s, for args: %s', self, args)
        for arg in args:
            if arg is None:
                logger.warning("Invalid PreResult object %s", self)
                return False
        return True

    def get_or_create(self):
        if not self.is_valid():
            return None, None
        result, created = games.models.Result.objects.get_or_create(
            home_goals=self.home_goals, away_goals=self.away_goals, minute=self.minute, type=self.result_type,
            final=self.is_final)
        self.event.add_result(result)
        return result, created
