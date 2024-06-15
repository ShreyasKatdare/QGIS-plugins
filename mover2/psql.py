import psycopg2

psql =  {
            "host":"localhost",
            "port":"5432",
            "user":"postgres",
            "password":"postgres",
            "database":"dolr"
        }


class PGConn:
    def __init__(self):
        self.details = psql
        self.conn = None

    def connection(self):
        """Return connection to PostgreSQL.  It does not need to be closed
        explicitly.  See the destructor definition below.

        """
        if self.conn is None:
            conn = psycopg2.connect(dbname=self.details["database"],
                                    host=self.details["host"],
                                    port=self.details["port"],
                                    user=self.details["user"],
                                    password=self.details["password"])
            self.conn = conn
            self.conn.autocommit = True
            
        return self.conn

    def __del__(self):
        """No need to explicitly close the connection.  It will be closed when
        the PGConn object is garbage collected by Python runtime.
        """
        print(self.conn)
        if self.conn is not None:
            self.conn.close()
        self.conn = None
        
def check_schema_exists(psql_conn, schema_name):
    sql_query=f"""
        select 
            schema_name 
        from 
            information_schema.schemata 
        where 
            schema_name='{schema_name}'
    """
    with psql_conn.connection().cursor() as curr:
        curr.execute(sql_query)
        schema_exists = curr.fetchone()
    if schema_exists is not None:
        return True
    else:
        return False

def create_schema(psql_conn, schema_name, delete_original = False):
    comment_schema_drop="--"
    if delete_original and check_schema_exists(psql_conn, schema_name):
            comment_schema_drop=""
        
    sql_query=f"""
        {comment_schema_drop} drop schema {schema_name} cascade;
        create schema if not exists {schema_name};
    """
    with psql_conn.connection().cursor() as curr:
        curr.execute(sql_query)
        
def drop_table(psql_conn, schema, table):
    sql = f'''
        drop table if exists {schema}.{table};
    '''
    with psql_conn.connection().cursor() as curr:
        curr.execute(sql)
        
def add_column(psql_conn, table, column, type):
    sql = f'''
        alter table {table}
        drop column if exists {column};
        alter table {table}
        add column {column} {type};
    '''
    with psql_conn.connection().cursor() as curr:
        curr.execute(sql)
    
def check_column_exists(psql_conn, schema, table, column):
    sql = f'''
    SELECT EXISTS (SELECT 1 
    FROM information_schema.columns 
    WHERE 
        table_schema='{schema}' 
    AND 
        table_name='{table}' 
    AND 
        column_name='{column}');
    '''
    with psql_conn.connection().cursor() as curr:
        curr.execute(sql)
        a = curr.fetchall()
    return a[0][0]

def find_column_geom_type(psql_conn, schema, table, column):
    sql = f'''
        select 
            type
        from 
            geometry_columns 
        where
            f_table_schema = '{schema}' 
            and 
            f_table_name = '{table}' 
            and 
            f_geometry_column = '{column}';
    '''
    with psql_conn.connection().cursor() as curr:
        curr.execute(sql)
        res = curr.fetchall()
    return res[0][0]

def find_dtype(psql_conn, schema, table, column):
    sql = f'''
        SELECT data_type
        FROM information_schema.columns
        WHERE table_schema = '{schema}' AND 
        table_name = '{table}' AND
        column_name = '{column}';
    '''
    with psql_conn.connection().cursor() as curr:
        curr.execute(sql)
        res = curr.fetchall()
    return res[0][0]


def find_srid(psql_conn, schema, table, column):
    sql = f'''
        select find_srid('{schema}','{table}','{column}')
    '''
    with psql_conn.connection().cursor() as curr:
        curr.execute(sql)
        res = curr.fetchall()
    return int(res[0][0])
    
def number_of_entries(psql_conn, schema, table):
    sql = f'''
    select 
        count(gid)
    from 
        {schema}.{table}
    '''
    with psql_conn.connection().cursor() as curr:
        curr.execute(sql)
        res = curr.fetchall()
    return int(res[0][0])

def copy_table(psql_conn, input, output):
    sql = f'''
        drop table if exists {output};
        create table {output} as table {input};
    '''
    with psql_conn.connection().cursor() as curr:
        curr.execute(sql)
        
def update_srid(psql_conn, input_table, column, srid):
    sql = f'''
        alter table {input_table}
        alter column {column} 
        type geometry(Geometry,{srid})
        using st_transform({column},{srid});
    '''
    with psql_conn.connection().cursor() as curr:
        curr.execute(sql)
        
def rename_column(psql_conn, input_schema, input_table_name, original, final):
    if not check_column_exists(psql_conn, input_schema,input_table_name,original):
        return
    
    sql = f'''
        alter table {input_schema}.{input_table_name}
        rename column {original} to {final};
    '''
    with psql_conn.connection().cursor() as curr:
        curr.execute(sql)
        
def add_gist_index(psql_conn, schema, table, column):
    sql = f"""
        create index if not exists
            {schema}_{table}_{column}_index 
        on 
            {schema}.{table}
        using 
            GIST({column});
    """
    with psql_conn.connection().cursor() as curr:
        curr.execute(sql)

def check_table_exists(psql_conn, schema, table):
    sql = f"""
        select exists (
            select
                * 
            from
                information_schema.tables 
            where  
                table_schema = '{schema}'
            and    
                table_name   = '{table}'
        );
    """
    with psql_conn.connection().cursor() as curr:
        curr.execute(sql)
        res = curr.fetchall()
    if res[0][0]:
        return True
    else:
        return False
    
def create_gist_index(psql_conn, schema, table, column):
    sql = f"""
        create index if not exists {schema}_{table}_{column}_index on {schema}.{table} using gist ({column});
    """
    with psql_conn.connection().cursor() as curr:
        curr.execute(sql)
    
    
def get_corner_nodes(psql_conn, input_topo_schema, output_schema, output_table, angle_thresh=45, only_trijunctions=False, face_id=None):
    cmt = '--' if face_id == None else ''
    angle_thresh = int(angle_thresh)
    sql = f'''
        drop table if exists {output_schema}.{output_table};
        create table {output_schema}.{output_table} as

        with neigh as (
            select
                count(p.edge_id) as count,
                n.node_id as node_id,
                n.geom as geom
            from
                {input_topo_schema}.edge_data as p,
                {input_topo_schema}.node as n
            where
                {cmt} (p.left_face = {face_id} or p.right_face = {face_id}) and
                (p.start_node = n.node_id
                or 
                p.end_node = n.node_id)
            group by
                n.node_id
        )

        select
            node_id,
            geom,
            count as degree
        from
            neigh
        where
            count > 2
        ;
    '''
    with psql_conn.connection().cursor() as curr:
        curr.execute(sql)
        
    if not only_trijunctions:
        bounds = [angle_thresh, 180-angle_thresh, 180+angle_thresh, 360-angle_thresh]
        sql_query = f"""
            insert into {output_schema}.{output_table}

            with neigh as (
                select
                    count(p.edge_id) as count,
                    n.node_id as node_id,
                    n.geom as geom
                from
                    {input_topo_schema}.edge as p,
                    {input_topo_schema}.node as n
                where
                    {cmt} (p.left_face = {face_id} or p.right_face = {face_id}) and
                    (p.start_node = n.node_id
                    or 
                    p.end_node = n.node_id)
                group by
                    n.node_id
            )
            
            select 
                n.node_id,
                n.geom,
                n.count as degree
            from 
                {input_topo_schema}.edge_data as p
            join 
                {input_topo_schema}.edge_data as q 
                on 
                    p.start_node = q.end_node
            join 
                neigh as n 
                on 
                    p.start_node = n.node_id    
            where
                {cmt} (p.left_face = {face_id} or p.right_face = {face_id}) and
                {cmt} (q.left_face = {face_id} or q.right_face = {face_id}) and
                n.count = 2
                and
                (
                    (
                        degrees(st_angle(p.geom,q.geom)) > {bounds[0]}
                        and 
                        degrees(st_angle(p.geom,q.geom)) < {bounds[1]}
                    )
                    or
                    (
                        degrees(st_angle(p.geom,q.geom)) > {bounds[2]}
                        and 
                        degrees(st_angle(p.geom,q.geom)) < {bounds[3]}
                    )
                )
            ;
        """
        with psql_conn.connection().cursor() as curr:
            curr.execute(sql_query)
            
            
def get_geom_type(psql_conn, table):
    sql = f"""
        select geometrytype(geom) as geometry_type
        from {table}
        limit 1;
    """
    with psql_conn.connection().cursor() as curr:
        curr.execute(sql)
        type = curr.fetchone()
        if type is None:
            print("ERROR")
            exit()
        
    return type[0]

def create_topo(psql_conn, schema, topo_schema, input_table, tol=0, srid=32643, simplify_tol = 0, seg=True):
    
    type = get_geom_type(psql_conn, schema+'.'+input_table)
    comment = "" if check_schema_exists(psql_conn, topo_schema) else "--"
    
    sql=f"""
        {comment} select DropTopology('{topo_schema}');
        with topo_id as (
            select
                topology_id
            from
                topology.layer
            where
                schema_name = '{schema}'
                and
                table_name = '{input_table}_t'
                and
                feature_column = 'topo'
        ),
        topo_name as (
            select 
                name
            from
                topology.topology as t,
                topo_id as tid 
            where
                t.id = tid.topology_id
            limit 1
        )
        select DropTopology(name) from topo_name;
        select CreateTopology('{topo_schema}', {srid}, {tol});
        
        drop table if exists {schema}.{input_table}_t;
        create table {schema}.{input_table}_t as table {schema}.{input_table};
        
        select AddTopoGeometryColumn('{topo_schema}', '{schema}', '{input_table}_t','topo', '{type}');
        
        update {schema}.{input_table}_t
        set topo = totopogeom(geom,'{topo_schema}',layer_id(findlayer('{schema}','{input_table}_t','topo')));

        update {topo_schema}.edge_data 
        set geom = coalesce(st_simplify(geom, {simplify_tol}),geom);

        --with points as (
        --    select
        --        (st_dumppoints(geom)).geom as geom
        --    from 
        --        {topo_schema}.edge_data
        --) 
        --select TopoGeo_AddPoint('{topo_schema}',geom, {tol}) from points;
    """
    
    with psql_conn.connection().cursor() as curr:
        curr.execute(sql)
        
    if seg:
        segmentize(psql_conn, topo_schema, tol)
        
def segmentize(psql_conn, topo_name, seg_tol, seg_length = 10000):
    sql_query=f"""
        with edges as (
            select edge_id, start_node, end_node, geom from {topo_name}.edge_data
        ),
        boundary as (
            select
                (st_dumppoints(st_segmentize(geom, {seg_length}))).geom as point
            from
                edges
        )
        
        select topogeo_addpoint('{topo_name}', point, {seg_tol}) from boundary;
    """
    
    with psql_conn.connection().cursor() as curr:
        curr.execute(sql_query)
        
