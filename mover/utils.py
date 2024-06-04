import numpy as np
from .postgres_utils import *

def add_akarbandh(psql_conn, input_table, akarbandh_table, akarbandh_col, common_col):        
    sql = f'''
        alter table {input_table}
        drop column if exists {akarbandh_col};

        alter table {input_table}
        add column {akarbandh_col} float;
    '''
    with psql_conn.connection().cursor() as curr:
        curr.execute(sql)
        
    sql = f'''
        update {input_table} as p
        set {akarbandh_col} = (select area from {akarbandh_table} where {common_col} = p.{common_col})
    '''
    with psql_conn.connection().cursor() as curr:
        curr.execute(sql)
        
def add_farm_intersection(psql_conn, schema, input_table, farmplots, column_name):

    add_column(psql_conn, schema+'.'+input_table, column_name, 'float')

    sql = f"""
        update {schema}.{input_table} as a
        set {column_name} = (
            select 
                st_area(
                    st_intersection(
                        a.geom,
                        b.geom
                    )
                )/st_area(a.geom)
            from 
                (select st_collect(geom) as geom from {schema}.{farmplots}) as b
        );
    """
    with psql_conn.connection().cursor() as curr:
        curr.execute(sql)
        
def add_farm_rating(psql_conn, schema, input_table, farmplots, column_name, method='all_avg'):
    
    add_column(psql_conn, schema+'.'+input_table, column_name, 'float')
    if method=='all_avg':
        sql = f"""
            update {schema}.{input_table} as a
            set {column_name} = coalesce((
                select 
                    avg( 
                        greatest(
                            st_area(
                                st_intersection(
                                    a.geom,
                                    b.geom
                                )
                            )/st_area(b.geom),
                            st_area(
                                st_difference(
                                    b.geom,
                                    a.geom
                                )
                            )/st_area(b.geom)
                        )
                    ) as rating
                    from
                        {schema}.{farmplots} as b
                    where
                        st_intersects(st_buffer(st_boundary(a.geom),20), b.geom)
            ),0);
        """
    elif method=='worst_3_avg':
        sql = f"""
            update {schema}.{input_table} as a
            set {column_name} = (
                select 
                    coalesce(avg(rating),0)
                from
                    (select 
                        greatest(
                            st_area(
                                st_intersection(
                                    a.geom,
                                    b.geom
                                )
                            )/st_area(b.geom),
                            st_area(
                                st_difference(
                                    b.geom,
                                    a.geom
                                )
                            )/st_area(b.geom)
                        ) as rating
                    from
                        {schema}.{farmplots} as b
                    where
                        st_intersects(st_buffer(st_boundary(a.geom),20), b.geom)
                    order by 
                        least(
                            st_area(
                                st_intersection(
                                    a.geom,
                                    b.geom
                                )
                            ),
                            st_area(
                                st_difference(
                                    b.geom,
                                    a.geom
                                )
                            )
                        )/st_area(b.geom) desc
                    limit 3) as a
            );
        """
    else:
        print("ERROR in farm rating calculation")
        return
        
    with psql_conn.connection().cursor() as curr:
        curr.execute(sql)
        

def add_excess_area(psql_conn, schema, input_table, farmplots, column_name):
    
    add_column(psql_conn, schema+'.'+input_table, column_name, 'float')

    sql = f"""
        update {schema}.{input_table} as a
        set {column_name} = (
            select 
                sum(
                    least(
                        st_area(
                            st_intersection(
                                a.geom,
                                b.geom
                            )
                        ),
                        st_area(
                            st_difference(
                                b.geom,
                                a.geom
                            )
                        )
                    )
                )/sum(st_area(b.geom))
            from
                {schema}.{farmplots} as b
            where
                st_intersects(st_buffer(st_boundary(a.geom),20), b.geom)
        );
    """
    with psql_conn.connection().cursor() as curr:
        curr.execute(sql)


def add_shape_index(psql_conn, schema, input_table, column_name):
    
    add_column(psql_conn, schema+'.'+input_table, column_name, 'float')

    sql = f"""
        update {schema}.{input_table} as a
        set {column_name} = st_perimeter(geom)*st_perimeter(geom)/st_area(geom);    
    """
    with psql_conn.connection().cursor() as curr:
        curr.execute(sql)
        
def calculate_varp_of_individual(points_list):
    points = points_list
    points.append(points_list[1])
    sum = 0
    for i in range(len(points)-2):
        a = np.array([float(points[i][0]), float(points[i][1])])
        b = np.array([float(points[i+1][0]), float(points[i+1][1])])
        c = np.array([float(points[i+2][0]), float(points[i+2][1])])

        ba = b - a
        bc = c - b
        if (np.linalg.norm(ba) * np.linalg.norm(bc)) == 0 or np.dot(ba, bc)==0:
            continue
        cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
        angle = np.arccos(min(cosine_angle,1))
        sum += abs(angle)

    return sum/(2*np.pi)

def get_all_gids(psql_conn, input_table):
    schema = input_table.split('.')[0]
    table = input_table.split('.')[1]
    
    if not check_column_exists(psql_conn, schema, table, 'gid'):
        print(f'GID does not exist in table {input_table}. Adding it as column name gid')
        add_column(psql_conn, input_table, 'gid', 'serial')
        
    sql = f'''
        select gid from {input_table} where not st_isempty(geom);
    '''
    with psql_conn.connection().cursor() as curr:
        curr.execute(sql)
        a = curr.fetchall()

    farm_gids = []

    for res in a:
        farm_gids.append(int(res[0]))
    
    return farm_gids
        
def add_varp(psql_conn, schema, input_table, column_name):
    farm_gids = get_all_gids(psql_conn, schema+'.'+input_table)
    
    add_column(psql_conn, schema+'.'+input_table, column_name, 'float')
    
    varp_sum = 0
    
    for farm_gid in farm_gids:
        sql = f'''
                select st_x(
                    (st_dumpPoints(geom)).geom),
                    st_y(
                        (st_dumpPoints(geom)).geom) 
                from 
                    {schema}.{input_table} 
                where
                    gid = {farm_gid};
            '''
        with psql_conn.connection().cursor() as curr:
            curr.execute(sql)
            res = curr.fetchall()
        varp = calculate_varp_of_individual(res)
        if np.isnan(varp):
            varp = 1
            varp_sum += varp
            continue
        varp_sum += varp
        sql = f'''
            update {schema}.{input_table}
            set {column_name} = {varp}
            where gid = {farm_gid};
        '''
        with psql_conn.connection().cursor() as curr:
            curr.execute(sql)
            
    if(len(farm_gids) == 0):
        return None
    return varp_sum/len(farm_gids)
    
