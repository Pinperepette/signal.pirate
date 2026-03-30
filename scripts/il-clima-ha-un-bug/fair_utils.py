"""Utility condivise per l'analisi di FaIR 2.2.4."""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from fair import FAIR
from fair.io import read_properties
from fair.interface import fill, initialise
import warnings
warnings.filterwarnings('ignore')

OUT = '/Users/pinperepette/Porgetti/fair/output'


def create_fair(scenarios, configs, time_start=1750, time_end=2100):
    """Crea un'istanza FaIR configurata con specie e dati RCMIP."""
    f = FAIR()
    f.define_time(time_start, time_end, 1)
    f.define_scenarios(scenarios)
    f.define_configs(configs)
    species, properties = read_properties()
    f.define_species(species, properties)
    f.allocate()
    f.fill_species_configs()
    f.fill_from_rcmip()
    return f


def set_climate(f, config, ohc, oht, doe=1.28, f4co2=8.0):
    """Imposta i parametri climatici per una configurazione."""
    fill(f.climate_configs['ocean_heat_capacity'], ohc, config=config)
    fill(f.climate_configs['ocean_heat_transfer'], oht, config=config)
    fill(f.climate_configs['deep_ocean_efficacy'], doe, config=config)
    fill(f.climate_configs['gamma_autocorrelation'], 1.0, config=config)
    fill(f.climate_configs['sigma_eta'], 0.0, config=config)
    fill(f.climate_configs['sigma_xi'], 0.0, config=config)
    fill(f.climate_configs['stochastic_run'], False, config=config)
    fill(f.climate_configs['forcing_4co2'], f4co2, config=config)


def init_fair(f):
    """Inizializza concentrazioni, forcing, temperatura."""
    initialise(f.concentration, f.species_configs['baseline_concentration'])
    initialise(f.forcing, 0)
    initialise(f.temperature, 0)
    initialise(f.cumulative_emissions, 0)
    initialise(f.airborne_emissions, 0)


def run_single(ohc, oht, doe, f4co2, fs_co2, aci_scale, scenario='ssp245'):
    """Esegue una singola run e ritorna (temperatura, timebounds)."""
    f = create_fair([scenario], ['run'])
    set_climate(f, 'run', ohc, oht, doe, f4co2)
    fill(f.species_configs['forcing_scale'], fs_co2, specie='CO2', config='run')
    fill(f.species_configs['aci_scale'], aci_scale, config='run')
    init_fair(f)
    f.run()
    temp = np.asarray(f.temperature.loc[dict(scenario=scenario, config='run', layer=0)])
    return temp, f.timebounds


def get_temp(f, scenario, config):
    """Estrae la temperatura superficiale da una run."""
    return np.asarray(f.temperature.loc[dict(scenario=scenario, config=config, layer=0)])


def savefig(name, dpi=150):
    """Salva il grafico corrente nella cartella output."""
    plt.tight_layout()
    plt.savefig(f'{OUT}/{name}', dpi=dpi, bbox_inches='tight')
    plt.close()
    print(f'  -> {name}')
