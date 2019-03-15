###############################################################################
# IBM(c) 2019 EPL license http://www.eclipse.org/legal/epl-v10.html
###############################################################################

# -*- coding: utf-8 -*-

from flask import g

from .app import dbi, dbsession, cache
from .noderange import NodeRange
from ..inventory.manager import InventoryFactory

OPT_QUERY_THRESHHOLD = 18


def get_nodes_list(ids=None):

    wants = []
    if ids:
        if type(ids) is list:
            wants.extend(ids)
        else:
            wants.append(ids)

    try:
        nodes = cache.get('nodes_list_all')
    except:
        # Error when connection cache
        nodes = None

    if nodes is None:
        # get wanted records from nodelist table
        nodes = dbi.gettab(['nodelist'], wants)
        if not wants:
            try:
                cache.set('nodes_list_all', nodes, timeout=60)
            except:
                pass

    if wants:

        results = dict()
        for key in wants:
            if key in nodes:
                results[key] = nodes.get(key)
    else:
        results = dict(nodes)

    return results


@cache.cached(timeout=50, key_prefix='get_node_basic')
def get_node_basic(id):

    return dbi.gettab(['nodelist'], [id])


def get_nodes_by_range(noderange=None):

    # parse the node range in literal to a list objects (might be node, group, or non existence)
    nr = NodeRange(noderange)

    # Get attributes from nodelist
    if nr.all or nr.size > OPT_QUERY_THRESHHOLD:
        # query whole if the range size larger than 255
        dataset = dbi.gettab(['nodelist', 'nodegroup'])
    else:
        dataset = dbi.gettab(['nodelist', 'nodegroup'], nr.nodes)

    g.nodeset = dataset
    if nr.all:
        return dataset.keys(), None

    nodelist = dict()
    nonexistence = list()
    for name in nr.nodes:
        if name in dataset:
            nodelist[name] = dataset[name]
        else:
            nonexistence.append(name)

    # For nonexistence, need to check if it is a group or tag
    return nodelist.keys(), nonexistence


def _check_groups_in_noderange(nodelist, noderange):
    unique_groups = set()  # unique group or tag name

    # get all group names
    for node, values in nodelist.iteritems():
        groups = values.get('nodelist.groups', '')
        if groups:
            unique_groups.update(groups.split(','))

    return list(unique_groups)


def get_nodes_by_list(nodelist=None):
    return dbi.gettab(['nodelist'], nodelist)


def get_hmi_by_list(nodelist=None):
    result = {}
    for node, values in dbi.gettab(['openbmc'], nodelist).iteritems():
        result[node] = {'bmcip': values.get('openbmc.bmc'), 'username': 'root', 'password': '0penBmc'}

    return result


@cache.memoize(timeout=50)
def get_node_attributes(node):

    target_node = get_nodes_list(node)
    if not target_node:
        return None

    groups = target_node.values()[0].get('nodelist.groups')

    # combine the attribute from groups
    needs = [node]
    needs.extend(groups.split(','))
    return get_node_inventory('node', needs)


def get_node_inventory(objtype, ids=None):
    hdl = InventoryFactory.createHandler('node', dbsession, None)


    wants = None
    if ids:
        if type(ids) is list:
            wants = ids
        else:
            wants = [ids]

    result = hdl.exportObjs(wants, None, fmt='json')
    if not result:
        return []

    # TODO: filter by objtype
    return result['node']