import awkward as ak
from coffea.nanoevents import NanoEventsFactory, NanoAODSchema
import numpy as np
import matplotlib.pyplot as plt

NanoAODSchema.warn_missing_crossrefs = False

fname = '/home/hatakeyamay/ana/MadJaxMC/cmseft/generation/job_all_tt01j_test.root'
#fname = 'nanogen_ttbar_starting.root'
events = NanoEventsFactory.from_root(
    fname,
    schemaclass=NanoAODSchema,
).events()

fname_fixed = '/cms/data/jsamudio/boosted/boostedttX/tt1j_sm_combined.root'
events_fixed = NanoEventsFactory.from_root(
    fname_fixed,
    schemaclass=NanoAODSchema,
).events()

# For tt HT
def get_yvals():
    genp = events.LHEPart
    pdgId = events.LHEPart.pdgId
    gen_st = events.LHEPart.status    
    genp_fixed = events_fixed.LHEPart
    pdgId_fixed = events_fixed.LHEPart.pdgId
    gen_st_fixed = events_fixed.LHEPart.status

    return ak.sum(genp[((abs(pdgId) == 6)) & (gen_st == 1)].pt, axis=-1), ak.sum(genp_fixed[((abs(pdgId_fixed) == 6)) & (gen_st_fixed == 1)].pt, axis=-1)

# For Z/H pT
#def get_yvals():
#    genp = events.LHEPart
#    pdgId = events.LHEPart.pdgId
#    gen_st = events.LHEPart.status    
#    genp_fixed = events_fixed.LHEPart
#    pdgId_fixed = events_fixed.LHEPart.pdgId
#    gen_st_fixed = events_fixed.LHEPart.status

#    return ak.sum(genp[(abs(pdgId) == 25) & (gen_st == 1)].pt, axis=-1), ak.sum(genp_fixed[(abs(pdgId_fixed) == 25) & (gen_st_fixed == 1)].pt, axis=-1)


def decode_WCnames(WCnames):
    WCnames_out = []
    WCname = ''
    for val in WCnames:
        fourchar = int(val).to_bytes(4, 'big').decode()
        if '-' in fourchar:
            WCname += fourchar.split('-')[-1]
        else:
            if len(WCname):
                WCnames_out.append(WCname)
            WCname = fourchar.lstrip('\x00')
    WCnames_out.append(WCname)
    return WCnames_out

WCnames = ["SM"] + decode_WCnames(events.WCnames[0])
print((WCnames))

def get_wc_weight(name='', value=0):
    sm_weight = events.EFTfitCoefficients[:,0]
    if name == 'sm':
        return sm_weight  
    else:
        wc_idx = WCnames.index(name)
        index1 = events.EFTfitCoefficientIndex1[0]
        index2 = events.EFTfitCoefficientIndex2[0]
        matching1 = np.where((index1 == wc_idx) & (index2 == 0))[0]
        matching2 = np.where((index1 == wc_idx) & (index2 == wc_idx))[0]
    
        wc = value
        wc_lin = ak.flatten(events.EFTfitCoefficients[:,matching1] * wc)
        wc_sq = ak.flatten(events.EFTfitCoefficients[:,matching2] * wc**2)
        wc_sum_weight = sm_weight + wc_lin + wc_sq

        return wc_sum_weight


def per_bin_variance(data, bin_edges):
    """
    Calculates the variance for each bin in a dataset.

    Args:
        data (array-like): The input data.
        bin_edges (array-like): The edges of the bins.

    Returns:
        array-like: An array containing the variance for each bin.
                     Returns an empty array if a bin is empty.
    """
    bin_indices = np.digitize(data, bin_edges)
    variances = []
    for i in range(1, len(bin_edges)):
        bin_data = data[bin_indices == i]
        if len(bin_data) > 0:
            variances.append(np.var(bin_data))
        else:
            variances.append(np.nan)
    return np.array(variances)
        
def plot_hist(total_mj, total_fixed, process, wc_name='', value=0):
    
    mj_weight = get_wc_weight(wc_name,value)
    fixed_weight = events_fixed['LHEWeight'][:]['originalXWGTUP']
    print('fixed xsec:', (np.sum(fixed_weight)/total_fixed))
    y_mj, y_fixed = get_yvals()

    import mplhep

    mplhep.style.use([mplhep.style.CMS, {"figure.figsize": (8, 8)}])
    
    from matplotlib.ticker import AutoMinorLocator, FormatStrFormatter
    fig, (ax1, ax2) = plt.subplots(2,1, sharex=True, gridspec_kw={'height_ratios':[3,1]})
    bins = np.arange(0,1500, 50)
    y1,binEdges = np.histogram(y_mj, bins=bins, weights=mj_weight/total_mj)
    y1sq, binedges = np.histogram(y_mj, bins=bins, weights=(mj_weight/total_mj)**2)
    y2,binEdges2 = np.histogram(y_fixed, bins=bins, weights=fixed_weight/total_fixed)
    y2sq,binedges2 = np.histogram(y_fixed, bins=bins, weights=(fixed_weight/total_fixed)**2)
    #print(y1, y2)
    bincenters = 0.5*(binEdges[1:]+binEdges[:-1])
    err_mj     = np.sqrt(y1sq)
    #print(err_mj)
    err_fixed = np.sqrt(y2sq)
    print("sumw^2:", np.sum(y2)**2)
    print("sumw2:", np.sum(y2sq))

    #y1 = y1/total_comp #here
    #err_mj = err_mj/total_comp
    #legend_mj = np.sum(mj_weight)/total_comp

    #y2 = y2/100 #here                                                                                   
    #err_fixed = err_mj/100
    #legend_fixed = np.sum(fixed_weight)/100
    
    width      = 50
    ax1.errorbar(
        bincenters,
        y1,
        yerr = err_mj,
        marker = '.',
        drawstyle = 'steps-mid', capsize=5, capthick=1,
        label = f'Madjax: {(np.sum(fixed_weight)/total_mj):.3f} pb'
    )
    ax1.errorbar(
        bincenters,
        y2,
        yerr = err_fixed,
        marker = '.',
        drawstyle = 'steps-mid', capsize=5, capthick=1,
        label = f'Fixed: {(np.sum(fixed_weight)/total_fixed):.3f} pb'
    )
    if wc_name == 'sm':
        ax1.set_title(f"{process} Standard Model")
    else:
        ax1.set_title(f'{process} {wc_name} = {value}')
    ax1.legend()
    ax1.set_ylabel('$\sigma$ / 50 GeV')
    #ax.set_xlabel('$p_{T}^{t\overline{t}}$')
    sum_err = np.sqrt(err_mj**2 + err_fixed**2)
    #print(sum_err)
    pull = (y2-y1)/sum_err
    #print(y2-y1)
    #print(sum_err)
    print(pull)
    
    ax2.errorbar(x=bincenters, y = pull, xerr=(bins[1:]-bins[:-1])/2,
                    fmt='.', color='k')
    ax2.xaxis.set_minor_locator(AutoMinorLocator())
    ax2.yaxis.set_major_formatter(FormatStrFormatter('%g'))
    ax2.yaxis.set_minor_locator(AutoMinorLocator())
    ax2.tick_params(which='both', direction='in', top=True, right=True, labelsize=10)
    ax2.set_ylabel(r'$\frac{y_{fixed}-y_{MJ}}{\sqrt{\sum_{i} \Delta y_i^2}} $')#, fontsize=10)
    #ax2.yaxis.set_label_coords(-0.05,0.45)
    #ax2.set_xlabel(r'$H_{T}^{t\bar{t}}$')#, fontsize=10)
    ax2.set_xlabel(r'$p_{T}^{Z}$')
    ax2.grid(True)
    #ax1.set_xscale("log")
    fig.subplots_adjust(
        top=0.88,
        bottom=0.11,
        left=0.11,
        right=0.88,
        hspace=0.0,
        wspace=0.2)
    plt.savefig("plotHT.pdf")
    
def get_wc_weight_2d(name1='', name2='', value1=0, value2=0):
    sm_weight = events.EFTfitCoefficients[:,0]

    wc_idx1 = WCnames.index(name1)
    wc_idx2 = WCnames.index(name2)
    index1 = events.EFTfitCoefficientIndex1[0]
    index2 = events.EFTfitCoefficientIndex2[0]
    #ii = events.EFTfitCoefficients[((index1 == 0) & (index2 == 0))][0]
    matching11 = np.where((index1 == wc_idx1) & (index2 == 0))[0]
    matching21 = np.where((index1 == wc_idx1) & (index2 == wc_idx1))[0]

    wc1 = value1
    #print(wc)
    wc_lin1 = ak.flatten(events.EFTfitCoefficients[:,matching11] * wc1)
    #print(wc_lin)
    wc_sq1 = ak.flatten(events.EFTfitCoefficients[:,matching21] * wc1**2)
    #print(wc_sq1)
    matching12 = np.where((index1 == wc_idx2) & (index2 == 0))[0]
    matching22 = np.where((index1 == wc_idx2) & (index2 == wc_idx2))[0]

    matching_cross = np.where((index1 == wc_idx1) & (index2 == wc_idx2))[0]

    wc2 = value2
    #print(wc)
    wc_lin2 = ak.flatten(events.EFTfitCoefficients[:,matching12] * wc2)
    #print(wc_lin)
    wc_sq2 = ak.flatten(events.EFTfitCoefficients[:,matching22] * wc2**2)
    #print(wc_sq2)

    wc_cross = ak.flatten(events.EFTfitCoefficients[:,matching_cross] * wc1 * wc2)
    #print(wc_cross)
    wc_sum_weight = sm_weight + wc_lin1 + wc_sq1 + wc_lin2 + wc_cross + wc_sq2
    #print('new xsec:', (events['LHEWeight']['originalXWGTUP'][0]*10000)*(np.sum(wc_sum_weight)/len(wc_sum_weight)))
    #print('new xsec:', np.sum(wc_sum_weight)*(10000/len(wc_sum_weight)))
    #print("wc sum", np.sum(wc_sum_weight))
    return wc_sum_weight

def plot_2d(process, wc_name1='', wc_name2=''):
    x = np.linspace(-10,10,61)
    y = np.linspace(-80,80,61)
    x, y = np.meshgrid(x, y)
    #print(len(x))
    weights = np.zeros_like(x)
    rows, cols = x.shape
    for i in range(rows):
        for j in range(cols):
            weights[i,j] = np.sum(get_wc_weight_2d(wc_name1, wc_name2, x[i,j], y[i,j]))**2/np.sum(get_wc_weight_2d(wc_name1, wc_name2, x[i,j], y[i,j])**2)#/(np.sum(get_wc_weight_2d(wc_name1, wc_name2, 1, 1))**2/np.sum(get_wc_weight_2d(wc_name1, wc_name2, 1, 1)**2))
            #print(weights[i,j])
    x = x.flatten()
    y = y.flatten()
    weights = weights.flatten()
    weights = weights/len(events['LHEWeight']['originalXWGTUP'])
    #print(len(weights))
    #print(len(x))
    #mj_weight = get_wc_weight(wc_name,value)
    #mj_weight = events['LHEWeight'][:]['originalXWGTUP']
    #fixed_weight = events_fixed['LHEWeight'][:]['originalXWGTUP']
    #print('new xsec:', (494.5)*(np.sum(fixed_weight)/len(fixed_weight)))
    #print('fixed xsec:', np.sum(fixed_weight))
    #print(np.sum(fixed_weight))
    #print(np.sum(events_fixed['genWeight']))
    #y_mj, y_fixed = get_yvals()

    #print(y_mj, mj_weight)
    import mplhep


    mplhep.style.use([mplhep.style.CMS, {"figure.figsize": (8, 8)}])
    
    from matplotlib.ticker import AutoMinorLocator, FormatStrFormatter
    H, xedges, yedges = np.histogram2d(x, y/5, bins=61, weights=weights, density=False)
    print(H)
    fig, ax = plt.subplots(1,1)
    im = ax.imshow(H.T, extent=[xedges[0], xedges[-1], yedges[0], yedges[-1]], cmap='viridis', vmin=0, vmax=1,aspect=.125, origin='lower')
    #im = ax.imshow(H, cmap='viridis', vmin=0, vmax=1,aspect='equal')
    #sns.histplot(x=x, y=y, weights=weights, bins=10, cbar=True)

    print("H shape: ", H.shape)
    cs = ax.contour(H.T,np.arange(0,1,0.05),extent=[xedges[0], xedges[-1], yedges[0], yedges[-1]], colors='k', vmin=0, vmax=1)
    cbar = plt.colorbar(im)
    #plt.clim(0, 1)
    ax.set_title('Effective sample size per event', fontsize=20)
    point = ax.scatter(2.855, 29.65, c='red')
    #point = ax.scatter(2.979, 32.96, c='red')
    #point = ax.scatter(0, 0, c='red')
    ax.clabel(cs ,fontsize=10)
    ax.set_xlabel(wc_name1)
    ax.set_ylabel(wc_name2)
    #ax.set_ylim(-10,10)
    plt.autoscale(False)

plot_hist(49, 100, 'tt','sm',0)
