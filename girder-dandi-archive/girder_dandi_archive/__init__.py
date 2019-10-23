# -*- coding: utf-8 -*-
import re

from girder.plugin import GirderPlugin
from girder.models.item import Item
from girder.utility import search


class GirderPlugin(GirderPlugin):
    DISPLAY_NAME = 'DANDI Archive'

    def load(self, info):
        search.addSearchMode('dandi', dandiSearchHandler)


def dandiSearchHandler(query, types, user=None, level=None, limit=0, offset=0):
    # TODO currently swallowing errors and returning empty list
    try:
        query = convert_search_to_mongo_query(query)
        items = list(Item().findWithPermissions(query=query, types=types, user=user))
        for item in items:
            item['_modelType'] = 'item'  # TODO why is this necessary to provide?
    except SyntaxError:
        items = []
    except ValueError:
        items = []
    return {'item': items}  # TODO similarly why is this necessary to provide?
    # TODO those are questions around the search handler api more than anything


def tokenize_search_string(search_string):
    search_string = search_string.lower()
    tokens = search_string.split()
    # use '+' as a space inside a token, e.g. nuo+li => 'nuo li'
    tokens = [token.replace('+', ' ') for token in tokens]
    return tokens


def extract_key_values(tokens):
    key_values = {}
    for tok in tokens:
        if ':' in tok:
            if tok == ':' or tok.count(':') > 1 or tok.startswith(':') or tok.endswith(':'):
                raise SyntaxError('Malformed key value pair')
            else:
                key, value = tok.split(':')
                values = key_values.get(key, [])
                values.append(value)
                key_values[key] = values
    return key_values


def add_search_key_values(key_values):
    search_keys = {
        # See https://www.crossref.org/blog/dois-and-matching-regular-expressions/
        'doi': {
            'arity': 'multiple',
            'regex': r"""^10.\d{4,9}/[-._;()/:a-zA-Z0-9]+$""",
            'values': [],
            'meta_key': 'related_publications',
        },
        'keyword': {'arity': 'multiple', 'values': [], 'meta_key': 'keywords'},
        'experimenter': {'arity': 'single', 'values': []},
        # TODO ?? how will we keep these clean and do searches
        # with spaces, commas, first name, last name, different spellings?
        # non-first name/last name, utf-8 ??
        # TODO most proximate issue is with space between first and last name
        'lab': {'arity': 'single', 'values': []},
        'institution': {'arity': 'single', 'values': []},
        'subject_id': {'arity': 'single', 'values': []},
        'identifier': {'arity': 'single', 'values': []},
        'session_id': {'arity': 'single', 'values': []},
        'units': {'arity': 'more_fewer', 'min': None, 'max': None, 'meta_key': 'number_of_units'},
        'electrodes': {
            'arity': 'more_fewer',
            'min': None,
            'max': None,
            'meta_key': 'number_of_units',
        },
    }
    for key, values in key_values.items():
        for value in values:
            if key not in search_keys.keys():
                # Check if a more_fewer key
                m = re.search('^(more|fewer)_(.*)_than$', key)
                if m:
                    more_fewer, search_key = m.group(1), m.group(2)
                    if (
                        search_key in search_keys.keys()
                        and search_keys[search_key]['arity'] == 'more_fewer'
                    ):
                        if more_fewer == 'more':
                            if search_keys[search_key]['min']:
                                raise ValueError('Only one value for %s allowed') % key
                            else:
                                search_keys[search_key]['min'] = value
                                continue
                        else:
                            if search_keys[search_key]['max']:
                                raise ValueError('Only one value for %s allowed') % key
                            else:
                                search_keys[search_key]['max'] = value
                                continue
            else:
                if search_keys[key]['arity'] == 'single' and len(search_keys[key]['values']) > 1:
                    raise ValueError('Only one value for %s allowed') % key
                search_keys[key]['values'].append(value)
                continue
            raise ValueError('Invalid key %s' % key)
    return search_keys


def validate_search_key_values(search_keys):
    for key, search_data in search_keys.items():
        if search_data['arity'] == 'more_fewer' and (search_data['min'] or search_data['max']):
            if search_data['min']:
                search_data['min'] = int(search_data['min'])
                if search_data['min'] < 0:
                    raise ValueError('%s min value must be at least 0' % key)
            if search_keys[key]['max']:
                search_data['max'] = int(search_data['max'])
                if search_data['max'] < 1:
                    raise ValueError('%s max value must be at least 1' % key)
            if (
                search_data['min']
                and search_data['max']
                and search_data['min'] >= search_data['max']
            ):
                raise ValueError('%s min value must be less than max value' % key)
        if 'regex' in search_keys[key]:
            for value in search_keys[key]['values']:
                result = re.match(search_keys[key]['regex'], value)
                if result is None:
                    raise ValueError('Invalid value %s for key %s' % (value, key))


def get_mongo_key(key, search_data):
    if 'meta_key' in search_data:
        search_term = search_data['meta_key']
    else:
        search_term = key
    search_term = 'meta.%s' % search_term
    return search_term


def get_mongo_value(search_arity, search_values):
    if search_arity == 'multiple' and len(search_values) > 1:
        mongo_value = {'$all': search_values}
    else:
        mongo_value = search_values[0]
    return mongo_value


def get_mongo_more_fewer_value(min, max):
    if min and max:
        return {'$gt': min, '$lt': max}
    else:
        if min:
            return {'$gt': min}
        if max:
            return {'$lt': max}


def build_query_from_query_terms(search_keys):
    # Convert a semantically valid query into Mongo.
    query = {}
    for key, search_data in search_keys.items():
        mongo_key = get_mongo_key(key, search_data)
        # set something with values, either single or multiple
        if 'values' in search_data and search_data['values']:
            query[mongo_key] = get_mongo_value(search_data['arity'], search_data['values'])
        elif search_data['arity'] == 'more_fewer' and (search_data['min'] or search_data['max']):
            query[mongo_key] = get_mongo_more_fewer_value(search_data['min'], search_data['max'])
    return query


def convert_search_to_mongo_query(search_string):
    tokens = tokenize_search_string(search_string)
    key_values = extract_key_values(tokens)
    search_keys = add_search_key_values(key_values)
    validate_search_key_values(search_keys)
    query = build_query_from_query_terms(search_keys)
    return query
