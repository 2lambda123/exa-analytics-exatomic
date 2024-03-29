## -*- coding: utf-8 -*-
## Copyright (c) 2015-2017, Exa Analytics Development Team
## Distributed under the terms of the Apache License 2.0
#"""
#NWChem PSP Data
######################################
#This module provides a container object that stores output data coming from
#NWChem's pseudopotential generation scheme. Note that parsable data is created
#only if debug printing is used. This module also provides functions that parse
#multiple files simultaneously.
#"""
#import pandas as pd
#import os
#from glob import glob
#from exa import Container
#from exa.mpl import qualitative, sns
#from .paw_ae import AEOutput
#from .paw_ps import PAWOutput
#
#
#def parse_psp_data(scratch, symbol=None):
#    """
#    Given an NWChem scratch directory parse all pseudopotential
#    information.
#    """
#    plts = glob(os.path.join(scratch, "*.dat"))
#    symbols = {}
#    for plt in plts:
#        base = os.path.basename(plt)
#        first = base.split(".")[0]
#        paw = False
#        if "_" in first:
#            paw = True
#            first = first.split("_")[0]
#        symbols[first] = paw
#    for sym, paw in symbols.items():
#        if paw:
#            if sym == symbol or symbol is None:
#                return parse_paw_psp(scratch, symbol)
#        else:
#            raise
#            #return parse_nc_psp(scratch, symbol)
#
#
#def parse_paw_psp(scratch, symbol):
#    """
#    """
#    # Parse AE and PS output data to get nl values
#    aeed = AEOutput(os.path.join(scratch, symbol + "_out"))
#    aeed.parse(recursive=True)
#    psed = PAWOutput(os.path.join(scratch, symbol + "_paw"))
#    psed.parse(recursive=True)
#    aenl = (aeed.data['n'].astype(str) + aeed.data['l'].astype(str)).tolist()
#    psnl = psed.data['nl'].tolist()
#    r = [r"$r$"]
#    # Parse AE orbital data
#    aeorb = pd.read_csv(os.path.join(scratch, symbol+"_orb.dat"),
#                        delim_whitespace=True, names=r+aenl)
#    del aeorb[aeorb.columns[0]]
#    aeorb.columns = [[r"$\psi_i(r)$"]*len(aenl), aenl]
#    # Parse PS orbital data
#    ps3nl = [nl for nl in psnl for i in range(3)]
#    psorb = pd.read_csv(os.path.join(scratch, symbol + "_paw.dat"),
#                        delim_whitespace=True, names=r+ps3nl)
#    del psorb[psorb.columns[0]]
#    psorb.columns = [[r"$\phi_i(r)$", r"$\tilde{\phi}_i(r)$",
#                      r"$\tilde{p}_i(r)$"]*len(psnl), ps3nl]
#    # Parse PS potential data
#    potnames = [r"$v(r)$", r"$\tilde{v}(r)$", r"$\hat{V}_{PS}$"]
#    potnames += [r"$V_{" + nl + "}$" for nl in psnl]
#    pspot = pd.read_csv(os.path.join(scratch, symbol + "_pot.dat"),
#                        delim_whitespace=True, names=r+potnames)
#    del pspot[pspot.columns[0]]
#    # Parse PS wfc data
#    ps2nl = [nl for nl in psnl for i in range(2)]
#    pstest = pd.read_csv(os.path.join(scratch, symbol + "_test.dat"),
#                         delim_whitespace=True, names=r+ps2nl)
#    del pstest[pstest.columns[0]]
#    pstest.columns = [[r"phi-ps0", r"psi-ps"]*len(psnl), ps2nl]
#    # Parse logrithmic derivatives tests
#    log = []
#    for path in glob(os.path.join(scratch, symbol + "*_scat_test.dat")):
#        angmom = path.split(os.sep)[-1].split("_")[1].upper()
#        ae_ = r"$D^{AE}_{" + angmom + "}(E)$"
#        ps_ = r"$D^{PS}_{" + angmom + "}(E)$"
#        df = pd.read_csv(os.path.join(path), delim_whitespace=True,
#                         names=["$E\ (au)$", ae_, ps_])
#        if len(log) > 0:
#            del df["$E\ (au)$"]
#        log.append(df)
#    if len(log) > 0:
#        log = pd.concat(log, axis=1).set_index("$E\ (au)$")
#    data = pd.concat((aeorb, psorb, pspot), axis=1)
#    data.index = psed.grid()
#    pstest.index = psed.grid()
#    return data, log, pstest, psed, aeed
#
#
#class PSPData(Container):
#    """
#    A container for storing discrete pseudopotentials and pseudo-waves
#    defined on a radial grid and used in plane wave calculations.
#
#    Note:
#        This container stores pseudopotential data for all atoms in the
#        calculation of interest.
#    """
#    def plot_log(self, **kwargs):
#        """Plot the logarithmic derivatives."""
#        n = len(self.log.columns)//2
#        # Get default values
#        style = kwargs.pop("style", ["-", "--"])
#        ylim = kwargs.pop("ylim", (-5, 5))
#        colors = kwargs.pop("c", None)
#        if colors is None:
#            colors = qualitative(n=n)
#        elif not isinstance(colors, (list, tuple)):
#            colors = [colors]*n
#        # Plot the figure
#        ax = sns.plt.subplot()
#        for i, col in enumerate(self.log.columns[::2]):
#            cols = [col, col.replace("AE", "PS")]
##            plotme = self.log.loc[(self.log[cols[0]] < ylim[1]) &
##                                  (self.log[cols[0]] > ylim[0]) &
##                                  (self.log[cols[1]] < ylim[1]) &
##                                  (self.log[cols[1]] > ylim[0]), cols]
#            ax = self.log[cols].plot(ax=ax, style=style, c=colors[i], alpha=[1.0, 0.5], **kwargs)
##            ax = plotme.plot(ax=ax, style=style, c=colors[i], **kwargs)
#        ax.set_ylim(*ylim)
#        return ax
#
#    def plot_wfc(self, xlim=(0, 10), **kwargs):
#        """Plot (AE) wave functions."""
#        nls = self.psed.data.loc[self.psed.data['fill'] > 0, "nl"]
#        cols = [col for col in self.data.columns if "psi" in col[0] and any(nl in col[1] for nl in nls)]
#        return self.data[cols].plot(xlim=xlim, **kwargs)
#
#    def plot_v(self, xlim=(0, 5), ylim=(-10, 10), legend=True, **kwargs):
#        """Plot the radial potential functions."""
#        cols = [col for col in self.data.columns if isinstance(col, str) and "v" in col.lower()]
#        n = len(cols) - 3
#        colors = kwargs.pop("c", None)
#        styles = kwargs.pop("style", None)
#        if colors is None:
#            colors = ["black", "gray", "lightgray"] + qualitative(n=n)
#        if styles is None:
#            styles = ["-", "-", "-"] + ["--"]*n
#        ax = sns.plt.subplot()
#        for i, col in enumerate(cols):
#            ax = self.data[col].plot(ax=ax, style=styles[i], c=colors[i], label=col, legend=legend, **kwargs)
#        ax.set_xlim(*xlim)
#        ax.set_ylim(*ylim)
#        return ax
#
#    def get_ae_rho(self, nl):
#        """Get the radial shell density."""
#        col = [col for col in self.data.columns if nl.upper() in col[1]][0]
#        shell = self.data[col].copy().to_frame()
#        rho = (r"$\rho_i(r)$", col[1])
#        shell[rho] = shell[col]**2
#        shell[(r"$r^2\rho_i(r)^2$", col[1])] = shell.index**2*shell[rho]
#        return shell
#
#    def get_nodal(self):
#        """Get node positions and max radial density."""
#        raise
##        nls = self.psed.data.loc[self.psed.data['fill'] > 0, "nl"]
##        for nl in nls:
##            shell = self.get_ae_rho(nl)
##            psi = shell[shell.columns[0]].values
##            nodes = psi[1:]*psi[:-1]
##            nodes = nodes[nodes < 0].tolist()
#
#
#    def plot_ae_rho(self, nl, xlim=(0, 8), **kwargs):
#        """Plot the radial density of a given shell."""
#        shell = self.get_ae_rho(nl)
#        return shell.plot(xlim=xlim, **kwargs)
#
#    def plot_ps(self, nl, **kwargs):
#        """Plot a given pseudo wave, projector, and AE reference."""
#        cols = [col for col in self.data.columns if nl.upper() in col]
#        vcol = [col for col in cols if "V" in col][0]
#        xlim = kwargs.pop("xlim", (0, 3.5))
#        ax = self.data[cols].plot(secondary_y=vcol, xlim=xlim, **kwargs)
#        return ax
#
#    def log_diff(self):
#        """Error in logarithmic differences."""
#        self._logs = []
#        for l in ("S", "P", "D", "F"):
#            cols = [col for col in self.log.columns if "{" + l + "}" in col]
#            if len(cols) == 2:
#                self.log[l] = self.log[cols[0]] - self.log[cols[1]]
#                self._logs.append(l)
#
#    def log_diff_estimate(self):
#        """Log diff errore."""
#        if "S" not in self.log.columns:
#            self.log_diff()
#        return self.log.loc[self._logs].abs().sum()
#
#    def __init__(self, path, symbol=None):
#        data, log, pstest, psed, aeed = parse_psp_data(path, symbol)
#        super(PSPData, self).__init__(data=data, log=log, pstest=pstest, psed=psed, aeed=aeed)
#
#
##
##
##def parse_nc_psp(paths):
##    """
##    """
##    pass
##
##
