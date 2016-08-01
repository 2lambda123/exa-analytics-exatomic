# -*- coding: utf-8 -*-
# Copyright (c) 2015-2016, Exa Analytics Development Team
# Distributed under the terms of the Apache License 2.0
'''
Orbital DataFrame
####################
Orbital information such as centers and energies. All of the dataframe structures
and functions associated with the
results of a quantum chemical calculation. The Orbital table itself
summarizes information such as centers and energies. The momatrix
table contains a C matrix as it is presented in quantum textbooks,
stored in a columnar format. The bound method square() returns the
matrix as one would write it out. This table should have dimensions
N_basis_functions * N_basis_functions. The DensityMatrix table stores
a triangular matrix in columnar format and contains a similar square()
method to return the matrix as we see it on a piece of paper.
'''
import re
import numpy as np
import pandas as pd
import sympy as sy
from traitlets import Unicode
from sympy import Add, Mul
from exa import DataFrame, Series
from exatomic._config import config
from exatomic.basis import lmap
from exatomic.algorithms.basis import solid_harmonics
from exatomic.field import AtomicField
from collections import OrderedDict


class Orbital(DataFrame):
    """
    +-------------------+----------+-------------------------------------------+
    | Column            | Type     | Description                               |
    +===================+==========+===========================================+
    | frame             | category | non-unique integer (req.)                 |
    +-------------------+----------+-------------------------------------------+
    | orbital           | int      | vector of MO coefficient matrix           |
    +-------------------+----------+-------------------------------------------+
    | label             | int      | label of orbital                          |
    +-------------------+----------+-------------------------------------------+
    | occupation        | float    | population of orbital                     |
    +-------------------+----------+-------------------------------------------+
    | energy            | float    | eigenvalue of orbital eigenvector         |
    +-------------------+----------+-------------------------------------------+
    | symmetry          | str      | symmetry designation (if applicable)      |
    +-------------------+----------+-------------------------------------------+
    | x                 | float    | orbital center in x                       |
    +-------------------+----------+-------------------------------------------+
    | y                 | float    | orbital center in y                       |
    +-------------------+----------+-------------------------------------------+
    | z                 | float    | orbital center in z                       |
    +-------------------+----------+-------------------------------------------+

    Note:
        Spin zero means alpha spin or unknown and spin one means beta spin.
    """
    _columns = ['frame', 'energy', 'occupation', 'spin', 'vector']
    _index = 'orbital'
    _groupby = ('frame', np.int64)
    _categories = {'spin': np.int64}

    def get_orbital(self, orb=-1, spin=0, index=None):
        if index is None:
            return self[(self['occupation'] > 0) & (self['spin'] == spin)].iloc[orb]
        else:
            return self.iloc[index]



class MOMatrix(DataFrame):
    """
    The MOMatrix is the result of solving a quantum mechanical eigenvalue
    problem in a finite basis set. Individual columns are eigenfunctions
    of the Fock matrix with eigenvalues corresponding to orbital energies.

    .. math::

        C^{*}SC = 1

    +-------------------+----------+-------------------------------------------+
    | Column            | Type     | Description                               |
    +===================+==========+===========================================+
    | basis_function    | int      | row of MO coefficient matrix              |
    +-------------------+----------+-------------------------------------------+
    | orbital           | int      | vector of MO coefficient matrix           |
    +-------------------+----------+-------------------------------------------+
    | coefficient       | float    | weight of basis_function in MO            |
    +-------------------+----------+-------------------------------------------+
    | frame             | category | non-unique integer (req.)                 |
    +-------------------+----------+-------------------------------------------+
    """
    # TODO :: add spin as a column and make it the first groupby?
    _columns = ['coefficient', 'basis_function', 'orbital']
    _indices = ['momatrix']
    #_traits = ['orbital']
    _groupbys = ['frame']
    _categories = {}

    #def _custom_traits(self):
    #    coefs = self.groupby('frame').apply(lambda x: x.pivot('basis_function', 'orbital', 'coefficient').fillna(value=0).values)
    #    coefs = Unicode(coefs.to_json(orient='values')).tag(sync=True)
    #    #coefs = Unicode('[' + sq.groupby(by=sq.columns, axis=1).apply(
    #    #            lambda x: x[x.columns[0]].values).to_json(orient='values') + ']').tag(sync=True)
    #    return {'momatrix_coefficient': coefs}

    def square(self, frame=0):
       return self[self['frame'] == frame].pivot('basis_function', 'orbital', 'coefficient').fillna(value=0)


class DensityMatrix(DataFrame):
    """
    The density matrix in a contracted basis set. As it is
    square symmetric, only n_basis_functions * (n_basis_functions + 1) / 2
    rows are stored.

    +-------------------+----------+-------------------------------------------+
    | Column            | Type     | Description                               |
    +===================+==========+===========================================+
    | chi1              | int      | first basis function                      |
    +-------------------+----------+-------------------------------------------+
    | chi2              | int      | second basis function                     |
    +-------------------+----------+-------------------------------------------+
    | coefficient       | float    | overlap matrix element                    |
    +-------------------+----------+-------------------------------------------+
    | frame             | category | non-unique integer (req.)                 |
    +-------------------+----------+-------------------------------------------+
    """
    _columns = ['chi1', 'chi2', 'coefficient']
    _groupby = ('frame', np.int64)
    _index = 'index'

    def square(self):
        nbas = np.round(np.roots([1, 1, -2 * self.shape[0]])[1])
        tri = self.pivot('chi1', 'chi2', 'coefficient').fillna(value=0)
        tri = tri + tri.T
        for i, val in enumerate(np.diag(tri)):
            tri.at[i, i] /= 2
        return tri

    @classmethod
    def from_momatrix(cls, momatrix, occvec):
        """
        A density matrix can be constructed from an MOMatrix by:
        .. math::

            D_{uv} = \sum_{i}^{N} C_{ui} C_{vi} n_{i}

        Args:
            momatrix (:class:`~exatomic.orbital.MOMatrix`): a C matrix
            occvec (:class:`~np.array` or similar): vector of len(C.shape[0])
                containing the occupations of each molecular orbital.

        Returns:
            ret (:class:`~exatomic.orbital.DensityMatrix`): The density matrix
        """
        # TODO :: jit these functions or call some jitted functions
        #         the double hit on doubly-nested for loops can be optimized.
        square = momatrix.square()
        mus, nus = square.shape
        dens = np.empty((mus, nus), dtype=np.float_)
        for mu in range(mus):
            for nu in range(nus):
                dens[mu, nu] = (square.loc[mu].values *
                                square.loc[nu].values * occvec).sum()
        retlen =  mus * (mus + 1) // 2
        ret = np.empty((retlen,), dtype=[('chi1', 'i8'),
                                         ('chi2', 'i8'),
                                         ('coefficient', 'f8')])
        cnt = 0
        for mu in range(mus):
            for nu in range(mu + 1):
                ret[cnt] = (mu, nu, dens[mu, nu])
                cnt += 1
        return cls(ret)



def _voluminate_gtfs(universe, xx, yy, zz, kind='spherical'):
    """
    Generate symbolic ordered spherical (in cartesian coordinates)
    Gaussian type function basis for the given universe.

    Args:
        universe: Atomic universe
        xx (array): Discrete values of x
        yy (array): Discrete values of y
        zz (array): Discrete values of z
        kind (str): 'spherical' or 'cartesian'

    Returns:
        ordered_gtf_basis (list): list of funcs
    """
    lmax = universe.basis_set['l'].max()
    universe.compute_cartesian_gtf_order(universe._cartesian_ordering_function)
    universe.compute_spherical_gtf_order(universe._spherical_ordering_function)
    ex, ey, ez = sy.symbols('x y z', imaginary=False)
    ordered_gtf_basis = []
    bases = universe.basis_set.groupby('set')
    sh = solid_harmonics(lmax, ex, ey, ez)
    for seht, x, y, z in zip(universe.atom['set'], universe.atom['x'],
                               universe.atom['y'], universe.atom['z']):
        bas = bases.get_group(seht).groupby('shell_function')
        rx = ex - x
        ry = ey - y
        rz = ez - z
        r2 = rx**2 + ry**2 + rz**2
        for f, grp in bas:
            l = grp['l'].values[0]
            if kind == 'spherical':
                sym_keys = universe.spherical_gtf_order.symbolic_keys(l)
            elif kind == 'cartesian':
                sym_keys = universe.cartesian_gtf_order.symbolic_keys(l)
            else:
                raise Exception("kind must be 'spherical' or 'cartesian' not {}".format(kind))
            shell_functions = {}
            if l == 1:
                functions = []
                sq2 = np.sqrt(2)
                for i, j, k in universe._cartesian_ordering_function(l):
                    functions.append(d * rx**int(i) * ry**int(j) * rz**int(k) * sy.exp(-alpha * r2))
                shell_functions['x'] = sq2 / 2 * (functions[0] + functions[1])
                shell_functions['y'] = 1 / sq2 * (functions[1] - functions[0])
                shell_functions['z'] = functions[2]
            else:
                for i, j, k in universe._cartesian_ordering_function(l):
                    function = 0
                    for alpha, d in zip(grp['alpha'], grp['d']):
                        function += d * rx**int(i) * ry**int(j) * rz**int(k) * sy.exp(-alpha * r2)
                    shell_functions['x' * i + 'y' * j + 'z' * k] = function
            if l == 0:
                print('l=', l, ' ml=', 0)
                ordered_gtf_basis.append(shell_functions[''])
            elif l == 1:
                for lv, ml in sym_keys:
                    print('l=', lv, ' ml=', ml)
                    key = str(sh[(lv, ml)])
                    key = ''.join(re.findall("[A-z]+", key))
                    ordered_gtf_basis.append(shell_functions[key])
            else:
                for lv, ml in sym_keys:
                    print('l=', lv, ' ml=', ml)
                    if type(sh[(lv, ml)]) == Mul:
                        coef, sym = sh[(lv, ml)].as_coeff_Mul()
                        sym = str(sym).replace('*', '')
                        ordered_gtf_basis.append(coef * shell_functions[sym])
                    elif type(sh[(lv, ml)]) == Add:
                        dic = list(sh[(lv, ml)].as_coefficients_dict().items())
                        coefs = [i[1] for i in dic]
                        syms = [str(i[0]) for i in dic]
                        func = 0
                        for coef, sym in zip(coefs, syms):
                        # TODO : this probably breaks for something like x**2z**2
                            if '**' in sym:
                                sym = sym[0] * int(sym[-1])
                                func += coef * shell_functions[sym]
                            else:
                                sym = sym.replace('*', '')
                                func += coef * shell_functions[sym]
                        ordered_gtf_basis.append(func)
    return ordered_gtf_basis


def add_cubic_field_from_mo(universe, rmin, rmax, nr, vector=None):
    """
    Create a cubic field from a given vector (molecular orbital).

    Args:
        universe (:class:`~exatomic.universe.Universe`): Atomic universe
        rmin (float): Starting point for field dimensions
        rmax (float): Ending point for field dimensions
        nr (float): Discretization of the field dimensions
        vector: None, list, or int corresponding to vector index to generate (None will generate all fields)

    Returns:
        fields (list): List of cubic fields corresponding to vectors
    """
    vectors = universe.momatrix.groupby('orbital')
    if isinstance(vector, int):
        vector = [vector]
    elif vector is None:
        vector = [key for key in vectors.groups.keys()]
    elif not isinstance(vector, list):
        raise TypeError()
    x = np.linspace(rmin, rmax, nr)
    y = np.linspace(rmin, rmax, nr)
    z = np.linspace(rmin, rmax, nr)
    dxi = x[1] - x[0]
    dyj = y[1] - y[0]
    dzk = z[1] - z[0]
    dv = dxi * dyj * dzk
#    x, y, z = meshgrid3d(x, y, z)
    # Get symbolic representations of the basis functions
    basis_funcs = _voluminate_gtfs(universe, x, y, z)
    if config['dynamic']['numba'] == '1':
        from numba import vectorize, float64
        nb = vectorize([float64(float64, float64, float64)], nopython=True)
        for i, func in enumerate(basis_funcs):
            func = sy.lambdify(('x', 'y', 'z'), func, 'numpy')
            basis_funcs[i] = nb(func)
    else:
        basis_funcs = [np.vectorize(func) for func in basis_funcs]
    nn = len(basis_funcs)
    n = len(vector)
    # At this point, basis_funcs contains non-normalized ufunc.
    # Now discretize and normalize the basis function values.
    bf_values = np.empty((nn, nr**3), dtype=np.float64)
    for i in range(nn):
        v = basis_funcs[i](x, y, z)
        v /= np.sqrt((v**2 * dv).sum())
        bf_values[i, :] = v
    # Finally, add basis function values to form vectors
    # (normalized molecular orbitals).
    values = np.empty((n, nr**3), dtype=np.float64)
    dxi = [dxi] * n
    dyj = [dyj] * n
    dzk = [dzk] * n
    dxj = [0.0] * n
    dxk = [0.0] * n
    dyi = [0.0] * n
    dyk = [0.0] * n
    dzi = [0.0] * n
    dzj = [0.0] * n
    nx = [nr] * n
    ny = [nr] * n
    nz = [nr] * n
    ox = [rmin] * n
    oy = [rmin] * n
    oz = [rmin] * n
    frame = np.empty((n, ), dtype=np.int64)
    label = np.empty((n, ), dtype=np.int64)
    i = 0
#    print('n', n)
#    print('nn', nn)
#    print('vectors')
#    print(type(vectors))
#    print(len(vectors))
    for vno, vec in vectors:
        if vno in vector:
            #frame[i] = universe.orbital.ix[vno, 'frame']
            label[i] = vno
            v = 0
            for c, f in zip(vec['coefficient'], vec['basis_function']):
                v += c * bf_values[f]
            v /= np.sqrt((v**2 * dv).sum())
            values[i, :] = v
            i += 1
    data = pd.DataFrame.from_dict({'dxi': dxi, 'dxj': dxj, 'dxk': dxk, 'dyi': dyi,
                                   'dyj': dyj, 'dyk': dyk, 'dzi': dzi, 'dzj': dzj,
                                   'dzk': dzk, 'nx': nx, 'ny': ny, 'nz': nz, 'label': label,
                                   'ox': ox, 'oy': oy, 'oz': oz, 'frame': [0] * n})#frame})
    values = [Series(v) for v in values.tolist()]
    return AtomicField(data, field_values=values)
