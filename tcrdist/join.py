from tcrdist.public import _neighbors_sparse_variable_radius, _neighbors_sparse_fixed_radius
import pandas as pd

def join_by_dist(
    csrmat,
    left_df,
    right_df,
    how = "inner",
    left_cols  = ['cdr3_b_aa','v_b_gene','j_b_gene','subject'],
    right_cols = ['cdr3_b_aa','v_b_gene','j_b_gene','subject'],
    left_suffix = '_x',
    right_suffix = '_y',
    max_n= 5,
    radius = 1,
    radius_list = None, 
    sort_by_dist = True):
    """
    Join two sets of clonotypes, based on a distance threshold 
    encoded in a sparse matrix. The TCRs in the Left-DataFrame, 
    are joined with TCRs in the Right-Dataframe, for up to `max_n` closest TCRs where 
    the paired distance is less that that specifed in the `radius` or `radius_list` arguments.
    
    Crucially, one must provide a scipy.sparse csr matrix which can be pre-computed using. 
    :py:func:`tcrdist.rep_funcs.compute_pws_sparse` or 
    :py:func:`tcrdist.reperotire.TCRrep.compute_sparse_rect_distances`
    
    It is also possible to join using a unique radius for each sequence in Left-DataFrame
    using the `radius_list` argument instead of the fixed `radius` argument. 
    However, if using a radius list, it must match the number of rows in the csrmat 
    and the number of rows in Left DataFrame (i.e., len(radius_list) == left_df.shape[1] ).
    
    Parameters 
    ----------
    
    csrmat : scipy.sparse.matrix
        rows must correspond to index of left_df
        columns must correspond to index of right_df
    left_df: pandas.DataFrame
        Clone DataFrame
    right_df: pandas.DataFrame
        Clone DataFrame
    how : str
        must be ['inner','left','outer'] 
        
        * 'inner' for intersection of matches between Left and Right DataFrames, droping rows where there is no match.
        
        * 'left' all (matched or unmatched) rows from left data.frame; i.e., it will produce NAs where there is no match in the Right DataFrame.
 
        * 'outer' is a FULL OUTER JOIN combines the results of both Left and Right DataFrame. Outer join and returns all (matched or unmatched) rows.

        * (hint: right joins are not possible, unless you switch input dataframe order and recompute the spase matrix)
        
    left_cols : list
        all columns to include in left_df
    right_cols : list
        all columns to include in right_df 
    left_suffix : str
        appends to left columns
    right_suffix : str
        appends to right columns
    max_neighors : int
        limit on number of neighbors to join per row. 
        For instance if a TCR has 100 neighbors only the first 10 rows in the right df will
        be included (this is to avoid massive blowup in cases where knowing 
        about a few neighbors would suffice)
    radius = int
        default is 1
    
    Returns
    -------
    left_right_df : pandas DataFrame
        concatenates rows from left and right dataframe for all sequences within a specified distance
    """
    assert how in ['inner','left','outer']
    if how == "inner":
        add_unmatched_left = False
        add_unmatched_right= False
    elif how == "left":
        add_unmatched_left = True
        add_unmatched_right= False
    elif how == "outer":
        add_unmatched_left = True
        add_unmatched_right= True
    
    if radius_list is None:
        nn = _neighbors_sparse_fixed_radius(csrmat = csrmat, radius = radius)
    else: 
        assert len(radius_list) == left_df.shape[0]
        nn = _neighbors_sparse_variable_radius(csrmat = csrmat, radius_list = radius_list)
    left_index = list()
    right_index = list()
    dists = list()

    for i,ns in enumerate(nn):
        l = len(ns)
        if l > 0:
            ds = csrmat[i,ns].data
            if sort_by_dist:
                # Sort n index by dist smallest to largest
                # sorted(zip([10,1,0,-1],[100,500,1,10000])) => [(-1, 10000), (0, 1), (1, 500), (10, 100)]
                # thus [n for d, n in sorted(zip([10,1,0,-1],[100,500,1,10000]))] => [10000, 1, 500, 100]
                ns_ds = [(n,d) for d, n in sorted(zip(ds, ns))]
                ns,ds = zip(*ns_ds)
            if l > max_n:
                l = max_n
            left_index.extend([i]*l)
            right_index.extend(ns[0:l])
            dists.extend(ds[0:l])

    left_selection        = left_df[left_cols].rename(columns ={k:f"{k}{left_suffix}" for k in left_cols}).iloc[left_index,].reset_index(drop = True)
    right_selection       = right_df[right_cols].rename(columns ={k:f"{k}{right_suffix}" for k in right_cols}).iloc[right_index,].reset_index(drop = True)
    left_right_df         = pd.concat([left_selection, right_selection], axis = 1) 
    left_right_df['dist'] = dists
    
    
    if add_unmatched_left:
        left_index_unmatched = sorted(list(set(left_df.index) - set(left_index)))
        left_df_unmatched = left_df[left_cols].rename(columns ={k:f"{k}{left_suffix}" for k in left_cols}).iloc[left_index_unmatched,].reset_index(drop = True)
        left_right_df = pd.concat([left_right_df,left_df_unmatched],axis= 0)
    if add_unmatched_right:
        right_index_unmatched = sorted(list(set(right_df.index) - set(right_index)))
        right_df_unmatched = right_df[right_cols].rename(columns ={k:f"{k}{right_suffix}" for k in right_cols}).iloc[right_index_unmatched,].reset_index(drop = True)
        left_right_df = pd.concat([left_right_df,right_df_unmatched],axis = 0)
        
    return left_right_df
  

 
