#!/usr/bin/python
# -*- coding: UTF-8 -*-

import melt
import mangledb
mangledb.InitMangle(False)
from config import *
cur=melt.conn.cursor()

def StatTableReCreate():
    cur.execute("DROP TABLE IF EXISTS fiosm_stat")
    cur.execute("""CREATE TABLE fiosm_stat(ao_all    integer,
   found     integer,
   street    integer,
   all_b     integer,
   found_b   integer,
   all_r    integer,
   found_r     integer,
   street_r    integer,
   all_b_r     integer,
   found_b_r   integer,
   aoguid    uuid
);""")

def AssocTableReCreate():
    cur.execute("DROP TABLE IF EXISTS "+prefix+pl_aso_tbl)
    cur.execute("CREATE TABLE "+prefix+pl_aso_tbl+"(aoguid UUID,  osm_admin bigint);")
    cur.execute("DROP TABLE IF EXISTS "+prefix+way_aso_tbl)
    cur.execute("CREATE TABLE "+prefix+way_aso_tbl+"(aoguid UUID,  osm_way  bigint);")

def AssocIdxCreate():
    cur.execute("CREATE INDEX "+prefix+pl_aso_tbl+"_aoguid_idx ON "+prefix+pl_aso_tbl+""" USING btree (aoguid);
CREATE INDEX """+prefix+pl_aso_tbl+"_osm_admin_idx ON "+prefix+pl_aso_tbl+""" USING btree (osm_admin);""")
    cur.execute("CREATE INDEX "+prefix+way_aso_tbl+"_aoguid_idx ON "+prefix+way_aso_tbl+""" USING btree (aoguid);
CREATE INDEX """+prefix+way_aso_tbl+"_osm_way_idx ON "+prefix+way_aso_tbl+""" USING btree (osm_way);""")

def AssocBTableReCreate():
    cur.execute("DROP TABLE IF EXISTS "+prefix+bld_aso_tbl)
    cur.execute("CREATE TABLE "+prefix+bld_aso_tbl+"(aoguid      UUID,  osm_build   bigint, point smallint);")

def AssocTriggersReCreate():
    cur.execute("""CREATE OR REPLACE FUNCTION on_del_poly () RETURNS trigger AS
   $BODY$
   BEGIN
      --remove houses
      DELETE FROM """+prefix+bld_aso_tbl+""" WHERE osm_build = OLD.osm_id AND point = 0;
      --remove place
      DELETE FROM """+prefix+pl_aso_tbl+""" WHERE osm_admin = OLD.osm_id;
      RETURN OLD;
   END;
   $BODY$
   LANGUAGE plpgsql   VOLATILE   COST 100""")
    cur.execute("""DROP TRIGGER IF EXISTS tr_del_poly ON public."""+prefix+poly_table)
    cur.execute("""CREATE TRIGGER tr_del_poly
   BEFORE DELETE ON public."""+prefix+poly_table+""" FOR EACH ROW
   EXECUTE PROCEDURE on_del_poly ();""")

    cur.execute("""CREATE OR REPLACE FUNCTION on_del_line () RETURNS trigger AS
   $BODY$
   BEGIN
      --remove street
      DELETE FROM """+prefix+way_aso_tbl+""" WHERE osm_way = OLD.osm_id;
      RETURN OLD;
   END;
   $BODY$
   LANGUAGE plpgsql   VOLATILE   COST 100""")
    cur.execute("""DROP TRIGGER IF EXISTS tr_del_line ON public."""+prefix+ways_table)
    cur.execute("""CREATE TRIGGER tr_del_line
   BEFORE DELETE ON public."""+prefix+ways_table+""" FOR EACH ROW
   EXECUTE PROCEDURE on_del_line ();""")
    
    cur.execute("""CREATE OR REPLACE FUNCTION on_del_f_house () RETURNS trigger AS
   $BODY$
   BEGIN
      DELETE FROM """+prefix+bld_aso_tbl+""" WHERE aoguid = OLD.houseguid;
      RETURN OLD;
   END;
   $BODY$
   LANGUAGE plpgsql VOLATILE COST 100""")
    cur.execute("""DROP TRIGGER IF EXISTS tr_del_f_house ON public.fias_house""")
    cur.execute("""CREATE TRIGGER tr_del_f_house
   BEFORE DELETE ON public.fias_house FOR EACH ROW
   EXECUTE PROCEDURE on_del_f_house ();""")

    cur.execute("""CREATE OR REPLACE FUNCTION on_del_f_ao () RETURNS trigger AS
   $BODY$
   BEGIN
      DELETE FROM """+prefix+way_aso_tbl+""" WHERE aoguid = OLD.aoguid;
      DELETE FROM """+prefix+pl_aso_tbl+""" WHERE aoguid = OLD.aoguid;
      RETURN OLD;
   END;
   $BODY$
   LANGUAGE plpgsql VOLATILE COST 100""")
    cur.execute("""DROP TRIGGER IF EXISTS tr_del_f_ao ON public.fias_addr_obj""")
    cur.execute("""CREATE TRIGGER tr_del_f_ao
   BEFORE DELETE ON public.fias_addr_obj FOR EACH ROW
   EXECUTE PROCEDURE on_del_f_ao ();""")

    cur.execute("""CREATE OR REPLACE FUNCTION on_del_place () RETURNS trigger AS
   $BODY$
   BEGIN
      --remove houses
      DELETE FROM """+prefix+bld_aso_tbl+""" WHERE EXISTS
        (SELECT houseguid FROM fias_house WHERE 
        fias_house.houseguid = """+prefix+bld_aso_tbl+""".aoguid AND fias_house.aoguid = OLD.aoguid);
      --remove subs
      DELETE FROM """+prefix+pl_aso_tbl+""" WHERE EXISTS
        (SELECT aoguid FROM fias_addr_obj WHERE 
        fias_addr_obj.aoguid = """+prefix+pl_aso_tbl+""".aoguid AND fias_addr_obj.parentguid = OLD.aoguid);
      --remove streets
      DELETE FROM """+prefix+way_aso_tbl+""" WHERE EXISTS
        (SELECT aoguid FROM fias_addr_obj WHERE
        fias_addr_obj.aoguid = """+prefix+way_aso_tbl+""".aoguid AND fias_addr_obj.parentguid = OLD.aoguid);
      RETURN OLD;
   END;
   $BODY$
   LANGUAGE plpgsql   VOLATILE   COST 100""")
    cur.execute("""DROP TRIGGER IF EXISTS tr_del_place ON public."""+prefix+pl_aso_tbl)
    cur.execute("""CREATE TRIGGER tr_del_place
   BEFORE DELETE ON public."""+prefix+pl_aso_tbl+""" FOR EACH ROW
   EXECUTE PROCEDURE on_del_place ();""")
    
    cur.execute("""CREATE OR REPLACE FUNCTION on_del_street () RETURNS trigger AS
   $BODY$
   BEGIN
      --remove houses
      DELETE FROM """+prefix+bld_aso_tbl+""" WHERE EXISTS
        (SELECT houseguid FROM fias_house WHERE 
        fias_house.houseguid = """+prefix+bld_aso_tbl+""".aoguid AND fias_house.aoguid = OLD.aoguid);
      RETURN OLD;
   END;
   $BODY$
   LANGUAGE plpgsql   VOLATILE   COST 100""")
    cur.execute("""DROP TRIGGER IF EXISTS tr_del_street ON public."""+prefix+way_aso_tbl)
    cur.execute("""CREATE TRIGGER tr_del_street
   BEFORE DELETE ON public."""+prefix+way_aso_tbl+""" FOR EACH ROW
   EXECUTE PROCEDURE on_del_street ();""")

def Subareas(osmid):
    '''Calculate subareas of relation by member role 'subarea'
    return dict with names as key and osmid as values
    '''
    if osmid>0:
        #applicable only to relation i.e. negative osmid
        return {}
    else:
        osmid=osmid*(-1)
    
    cur.execute("SELECT members FROM "+prefix+slim_rel_tbl+" WHERE id=%s",(osmid,))
    mem=cur.fetchone()
    if mem==None:
        return {}
    mem=mem[0]
    mem=zip(mem[1::2],mem[::2])#osm2pgsql use sequence to represent roles
    mem=[it[1] for it in mem if it[0]=='subarea' and (it[1][0]=='r' or it[1][0]=='w')]
    #relation stored with negative osmid 
    mem=[int(it[1:])*(-1 if it[0]=='r' else 1) for it in mem]
    
    res={}
    for id_a in mem:
        #using only valid polygons i.e. processed by osm2pgsql
        cur.execute('SELECT name FROM '+prefix+poly_table+' WHERE osm_id=%s ',(id_a,))
        name=cur.fetchone()
        if name:
            res[name[0]]=id_a
    return res

def FindCandidates(pgeom,elem,tbl=prefix+poly_table,addcond=""):
    '''Get elements that may be osm representation of elem
    That items must contain part of elem's name full or formal (this will be returned)
    and lies within polygon pgeom (polygon of parent territory)
    
    return ( [(name, osmid),..],formal)
    '''
    formal=True
    name='%'+elem.formalname+'%'
    if pgeom==None:
        cur.execute("SELECT name, osm_id FROM "+tbl+" WHERE lower(name) LIKE lower(%s)"+addcond,(name,))
    else:
        cur.execute("SELECT name, osm_id FROM "+tbl+" WHERE lower(name) LIKE lower(%s) AND ST_Within(way,%s)"+addcond,(name,pgeom))
    res=cur.fetchall()
    if not res:
        if elem.offname==None or elem.formalname==elem.offname:
            return (None,None)
        name='%'+elem.offname+'%'
        if pgeom==None:
            cur.execute("SELECT name, osm_id FROM "+tbl+" WHERE lower(name) LIKE lower(%s)"+addcond,(name,))
        else:
            cur.execute("SELECT name, osm_id FROM "+tbl+" WHERE lower(name) LIKE lower(%s) AND ST_Within(way,%s)"+addcond,(name,pgeom))
        res=cur.fetchall()
        if res:
            formal=False
        else:
            return (None,None)
    
    return (res,formal)


def FindMangled(pgeom, elem, tbl=prefix + ways_table, addcond=""):
    '''Get osm representation of elem using name from streetmangler
    That items must lies within polygon pgeom (polygon of parent territory)

    return (name, osmid)
    '''
    if melt.mangledb.usable:
        mangl_n = melt.mangledb.db.CheckCanonicalForm(elem.shortname + " " + elem.formalname)
        if not mangl_n:
            return
    else:
        return
    if pgeom == None:
        cur.execute("SELECT name, osm_id FROM " + tbl + " WHERE lower(name) = lower(%s)" + addcond, (mangl_n,))
    else:
        cur.execute("SELECT name, osm_id FROM " + tbl + " WHERE lower(name) = lower(%s) AND ST_Within(way,%s)" + addcond, (mangl_n, pgeom))
    return cur.fetchall()


def FindAssocPlace(elem,pgeom):
    (candidates,formal)=FindCandidates(pgeom,elem,prefix+poly_table," AND building ISNULL")
    if not candidates:
        return None
    for name in elem.names(formal):
        checked=[it[1] for it in candidates if it[0].lower()==name.lower()]
        if checked:
            elem.name = name
            return checked[0]

def FindAssocStreet(elem,pgeom):
    mangled = FindMangled(pgeom, elem, prefix + ways_table, " AND highway NOTNULL")
    if mangled:
        elem.name = mangled[0][0]
        return [it[1] for it in mangled]
    (candidates,formal)=FindCandidates(pgeom,elem,prefix+ways_table," AND highway NOTNULL")
    if not candidates:
        return None
    for name in elem.names(formal):
        checked=[it[1] for it in candidates if it[0].lower()==name.lower()]
        if checked:
            mangledb.AddMangleGuess(name)
            elem.name = name
            return checked


def AssocBuild(elem, point):
    '''Search and save building association for elem
    '''
    if point:
        cur.execute("""SELECT osm_id, "addr:housenumber" FROM """ + prefix + point_table + """ WHERE "addr:street"=%s AND ST_Within(way,%s)""", (elem.name, elem.geom))
    else:
        cur.execute("""SELECT osm_id, "addr:housenumber" FROM """ + prefix + poly_table + """ WHERE "addr:street"=%s AND ST_Within(way,%s)""", (elem.name, elem.geom))
    osm_h = cur.fetchall()
    if not osm_h:
        return []
    #Filtering of found is optimisation for updating and also remove POI with address
    found_pre = set([h.onestr for h in elem.subHO('found_b')])
    osm_h = filter(lambda it: it[1] not in found_pre, osm_h)
    found = {}
    for hid, number in osm_h:
        for house in tuple(elem.subHO('not found_b')):
            if house.equal_to_str(number):
                found[hid] = house.guid
                #found.append({'h_id': hid, 'guid': house.guid})
    melt.conn.autocommit=False
    for myrow in found.iteritems():
        cur.execute("INSERT INTO " + prefix + bld_aso_tbl + " (aoguid,osm_build,point) VALUES (%s, %s, %s)", (myrow[1], myrow[0], point))
    melt.conn.commit()
    melt.conn.autocommit=True


def AssociateO(elem):
    '''Search and save association for all subelements of elem
    
    This function should work for elements with partitially associated subs 
    as well as elements without associated subs 
    '''
    if not elem.kind:
        return
    AssocBuild(elem, 0)
    AssocBuild(elem, 1)
    #run processing for found to parse their subs
    for sub in tuple(elem.subAO('found', False)):
        AssociateO(melt.fias_AONode(sub))
    #find new elements for street if any
    for sub in tuple(elem.subAO('street', False)):
        sub_ = melt.fias_AONode(sub)
        streets=FindAssocStreet(sub_,elem.geom)
        if streets<>None:
            melt.conn.autocommit=False
            for street in streets:
                cur.execute("SELECT osm_way FROM "+prefix+way_aso_tbl+" WHERE osm_way=%s",(street,))
                if not cur.fetchone():
                    cur.execute("INSERT INTO " +  prefix+way_aso_tbl + " (aoguid,osm_way) VALUES (%s, %s)", (sub.guid, street))
            melt.conn.commit()
            melt.conn.autocommit=True
            AssociateO(sub_)
    #search for new elements
    subareas=Subareas(elem.osmid)
    for sub in tuple(elem.subAO('not found', False)):
        sub_ = melt.fias_AONode(sub)
        adm_id=None
        if subareas:
            for name in sub_.names():
                adm_id=subareas.get(name)
                if adm_id:
                    del subareas[name]
                    break
                
        if adm_id==None:
            adm_id=FindAssocPlace(sub_,elem.geom)
        if not adm_id==None:
            cur.execute("INSERT INTO " + prefix + pl_aso_tbl + " (aoguid,osm_admin) VALUES (%s, %s)", (sub.guid, adm_id))
            elem.child_found(sub, 'found')
            sub_.osmid = adm_id
            sub_.kind = 2
            AssociateO(sub_)
        else:
            streets=FindAssocStreet(sub_,elem.geom)
            if streets<>None:
                melt.conn.autocommit=False
                for street in streets:
                    cur.execute("INSERT INTO " + prefix + way_aso_tbl + " (aoguid,osm_way) VALUES (%s, %s)", (sub.guid, street))
                melt.conn.commit()
                melt.conn.autocommit=True
                elem.child_found(sub, 'street')
                sub_.kind = 1
                sub_.osmid = streets[0]
                AssociateO(sub_)
    elem.stat('not found_r')
    elem.stat('not found_b_r')


def AssORoot():
    '''Associate and process federal subject (they have no parent id and no parent geom)
    '''
    cur.execute("SELECT aoguid FROM fias_addr_obj f WHERE parentguid is Null")
    fedobj = [it[0] for it in cur.fetchall()]
    for sub in fedobj:
        child=melt.fias_AONode(sub)
        if not child.kind:
            adm_id=FindAssocPlace(child,None)
            if not adm_id==None:
                cur.execute("INSERT INTO "+prefix+pl_aso_tbl+" (aoguid,osm_admin) VALUES (%s, %s)",(sub,adm_id))
                child=melt.fias_AONode(sub,2,adm_id)
        
        AssociateO(child)
        print child.name.encode('UTF-8') + str(child.kind)


def AssORootM():
    '''Associate and process federal subject (they have no parent id and no parent geom)
    '''
    from multiprocessing import Pool
    pool = Pool()
    results = []
    cur.execute("SELECT aoguid FROM fias_addr_obj f WHERE parentguid is Null")
    fedobj = [it[0] for it in cur.fetchall()]
    for sub in fedobj:
        child = melt.fias_AONode(sub)
        if not child.kind:
            adm_id = FindAssocPlace(child, None)
            if not adm_id == None:
                cur.execute("INSERT INTO " + prefix + pl_aso_tbl + " (aoguid,osm_admin) VALUES (%s, %s)", (sub, adm_id))
                child = melt.fias_AONode(sub, 2, adm_id)
        results.append(pool.apply_async(AssociateO, (child,)))

    while results:
        result = results.pop(0)
        result.get()


if __name__=="__main__":
    AssocTableReCreate()
    AssocBTableReCreate()
#    AssocTriggersReCreate()
    StatTableReCreate()
    AssORootM()
    AssocIdxCreate()
