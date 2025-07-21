from coffea import processor
from coffea.nanoevents import NanoAODSchema
from coffea.nanoevents import NanoEventsFactory
import numpy as np
import awkward as ak
import hist
from hist import Hist
from hist import axis, storage
from coffea import processor
import coffea.hist
from coffea.processor import AccumulatorABC

NanoAODSchema.warn_missing_crossrefs = False

# Processor parameters
total_mj = 5 #number of MadJax jobs listed in json file 
total_fixed = 1 #number of fixed files included
fname_fixed = "/cms/data/hatakeyamay/ana/MadJaxMC/cmseft/generation/jobs_complete/fixed/nanogen_0.root"
wc_name = "sm"
value = 0
list_title = "Nanogen_1M" #title in 

class HistAccumulator(AccumulatorABC):
    def __init__(self, hist):
        self._hist = hist

    def add(self, other):
        self._hist += other._hist
        return self

    def identity(self):
        return HistAccumulator(self._hist.copy().reset())
    
    def fill(self, **kwargs):
        self._hist.fill(**kwargs)

    @property
    def value(self):
        return self._hist
    
    def hist(self):
        return self._hist  
class AnalysisProcessor(processor.ProcessorABC):
    def __init__(self, fname_fixed, total_mj, total_fixed, wc_name, value):
        self.fname_fixed = fname_fixed
        self.total_mj = total_mj
        self.total_fixed = total_fixed
        self.wc_name = wc_name
        self.value = value

        # Histogram setup
        binning = axis.Regular(30, 0, 1500, name="ht", label="HT [GeV]")

        self._accumulator = processor.dict_accumulator({
            "ht_madjax": HistAccumulator(Hist(binning, storage=storage.Weight())),
            "ht_fixed": HistAccumulator(Hist(binning, storage=storage.Weight())),
        })
        # Pre-load fixed sample once
        self.events_fixed = NanoEventsFactory.from_root(
            self.fname_fixed,
            schemaclass=NanoAODSchema,
        ).events()
        self.fixed_ht = self.get_ht(self.events_fixed)
        self.fixed_weight = self.events_fixed.LHEWeight.originalXWGTUP / self.total_fixed

    @property
    def accumulator(self):
        return self._accumulator

    def get_ht(self, events):
        genp = events.LHEPart
        tops = genp[(abs(genp.pdgId) == 6) & (genp.status == 1)]
        return ak.sum(tops.pt, axis=-1)
    
    @staticmethod
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

    def get_wc_weight(self, events):
        sm_weight = events.EFTfitCoefficients[:,0]
        WCnames = ["SM"] + self.decode_WCnames(events.WCnames[0])
        if self.wc_name == 'sm':
            return sm_weight
        else:
            wc_idx = WCnames.index(self.wc_name)
            index1 = events.EFTfitCoefficientIndex1[0]
            index2 = events.EFTfitCoefficientIndex2[0]
            matching1 = np.where((index1 == wc_idx) & (index2 == 0))[0]
            matching2 = np.where((index1 == wc_idx) & (index2 == wc_idx))[0]
            
            wc = self.value
            wc_lin = ak.flatten(events.EFTfitCoefficients[:,matching1] * wc)
            wc_sq = ak.flatten(events.EFTfitCoefficients[:,matching2] * wc**2)
            wc_sum_weight = sm_weight + wc_lin + wc_sq
            
            return wc_sum_weight
    
    def process(self, events):
        output = self.accumulator.identity()
        ht_mj = self.get_ht(events)
        weight_mj = self.get_wc_weight(events)
        #print("here", events.fields)

        #self._accumulator["ht_madjax"].value.fill(ht=ak.to_numpy(ht_mj), weight=ak.to_numpy(weight_mj))
        #self._accumulator["ht_fixed"].value.fill(ht=ak.to_numpy(self.fixed_ht), weight=ak.to_numpy(self.fixed_weight))

        output["ht_madjax"].fill(ht=ak.to_numpy(ht_mj), weight=ak.to_numpy(weight_mj))
        output["ht_fixed"].fill(ht=ak.to_numpy(self.fixed_ht), weight=ak.to_numpy(self.fixed_weight))

        return output

    def postprocess(self, accumulator):
        return accumulator

import json
from coffea import processor

# Load dataset file list
with open("list_samples.json") as fin:
    filesets = json.load(fin)

# Example: select a few datasets from the json file
subset = {k: v for k, v in filesets.items() if k in [list_title]}

# Instantiate processor
proc = AnalysisProcessor(fname_fixed, total_mj, total_fixed, wc_name, value)

# Run job
out, metrics = processor.run_uproot_job(
    subset,
    "Events",
    proc,
    processor.iterative_executor,
    {
        "schema": NanoAODSchema,
        "savemetrics": True,
    },
)

import numpy as np
import uproot
import matplotlib.pyplot as plt
import mplhep
mplhep.style.use("CMS")
print(" out ", out)

# Write histograms to ROOT file
with uproot.recreate("ht_comparison.root") as fout:
    fout["ht_madjax"] = out["ht_madjax"].value
    fout["ht_fixed"] = out["ht_fixed"].value

# Extract histograms
#h1 = out["ht_madjax"].value()[()]
#h2 = out["ht_fixed"].value()[()]

h1 = out["ht_madjax"].hist()
h2 = out["ht_fixed"].hist()

# Bin centers and values
bin_centers = h1.axes[0].centers
y1 = h1.values()[()]
y2 = h2.values()[()]
print(" y1 ", y1)
print(" y2 ", y2)

err1 = np.sqrt(h1.variances())
err2 = np.sqrt(h2.variances())

# Pull calculation with protection against divide-by-zero
pull = np.divide(
    (y2 - y1), np.sqrt(err1**2 + err2**2),
    out=np.zeros_like(y1), where=(err1**2 + err2**2) > 0
)

# Plotting
fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True,
                               gridspec_kw={'height_ratios': [3, 1]},
                               figsize=(8, 8))

ax1.errorbar(bin_centers, y1, yerr=err1, fmt='o', label='Madgraph')
ax1.errorbar(bin_centers, y2, yerr=err2, fmt='o', label='Fixed')
ax1.legend()
ax1.set_ylabel("σ / bin")
ax1.set_title("HT (top quarks)")

ax2.errorbar(bin_centers, pull, fmt='k.')
ax2.set_ylabel("Pull")
ax2.axhline(0, linestyle='--', color='gray')
ax2.set_xlabel("HT [GeV]")

plt.tight_layout()
plt.savefig("ht_comparison_plot.pdf")

