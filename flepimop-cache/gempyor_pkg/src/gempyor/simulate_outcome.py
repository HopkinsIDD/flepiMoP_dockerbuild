#!/usr/bin/env python

##
# @file
# @brief Runs outcomes model after an SEIR run
#
# @details
#
# ## Configuration Items
#
# ```yaml
# outcomes:
#  method: delayframe                   # Only fast is supported atm. Makes fast delay_table computations. Later agent-based method ?
#  paths:
#    param_from_file: TRUE               #
#    param_place_file: <path.csv>       # OPTIONAL: File with param per csv. For each param in this file
#  scenarios:                           # Outcomes scenarios to run
#    - low_death_rate
#    - mid_death_rate
#  settings:                            # Setting for each scenario
#    low_death_rate:
#      new_comp1:                               # New compartement name
#        source: incidence                      # Source of the new compartement: either an previously defined compartement or "incidence" for diffI of the SEIR
#        probability:  <random distribution>           # Branching probability from source
#        delay: <random distribution>                  # Delay from incidence of source to incidence of new_compartement
#        duration: <random distribution>               # OPTIONAL ! Duration in new_comp. If provided, the model add to it's
#                                                      #output "new_comp1_curr" with current amount in new_comp1
#      new_comp2:                               # Example for a second compatiment
#        source: new_comp1
#        probability: <random distribution>
#        delay: <random distribution>
#        duration: <random distribution>
#      death_tot:                               # Possibility to combine compartements for death.
#        sum: ['death_hosp', 'death_ICU', 'death_incid']
#
#    mid_death_rate:
#      ...
#
# ## Input Data
#
# * <b>{param_place_file}</b> is a csv with columns place, parameter, value. Parameter is constructed as, e.g for comp1:
#                probability: Pnew_comp1|source
#                delay:       Dnew_comp1
#                duration:    Lnew_comp1


# ## Output Data
# * {output_path}/model_output/{setup_name}_[scenario]/[simulation ID].hosp.parquet


## @cond
import multiprocessing
import pathlib
import time, os

import click

from gempyor import file_paths, setup
from gempyor.utils import config
from gempyor import outcomes


@click.command()
@click.option(
    "-c",
    "--config",
    "config_file",
    envvar="CONFIG_PATH",
    type=click.Path(exists=True),
    required=True,
    help="configuration file for this simulation",
)
@click.option(
    "-d",
    "--scenarios_outcomes",
    "scenarios_outcomes",
    envvar="FLEPI_DEATHRATES",
    type=str,
    default=[],
    multiple=True,
    help="Scenario of outcomes to run",
)
@click.option(
    "-n",
    "--nslots",
    envvar="FLEPI_NUM_SLOTS",
    type=click.IntRange(min=1),
    help="override the # of outcomes simulation to run runs in the config file",
)
@click.option(
    "-i",
    "--first_sim_index",
    envvar="FIRST_SIM_INDEX",
    type=click.IntRange(min=1),
    default=1,
    show_default=True,
    help="The index of the first simulation to run against",
)
@click.option(
    "-j",
    "--jobs",
    envvar="FLEPI_NJOBS",
    type=click.IntRange(min=1),
    default=multiprocessing.cpu_count(),
    show_default=True,
    help="the parallelization factor",
)
@click.option(
    "-O",
    "--out-id",
    "out_run_id",
    envvar="FLEPI_RUN_INDEX",
    type=str,
    default=file_paths.run_id(),
    show_default=True,
    help="unique identifier for the run",
)
@click.option(
    "-I",
    "--in-id",
    "in_run_id",
    envvar="FLEPI_RUN_INDEX",
    type=str,
    default=file_paths.run_id(),
    show_default=True,
    help="unique identifier for the run",
)
@click.option(
    "--out-prefix",
    "--out-prefix",
    "out_prefix",
    envvar="FLEPI_PREFIX",
    type=str,
    default=None,
    show_default=True,
    help="unique identifier for the run",
)
@click.option(
    "--in-prefix",
    "--in-prefix",
    "in_prefix",
    envvar="FLEPI_PREFIX",
    type=str,
    default=None,
    show_default=True,
    help="unique identifier for the run",
)
@click.option(
    "--stoch_traj_flag",
    "--stoch_traj_flag",
    "stoch_traj_flag",
    envvar="FLEPI_STOCHASTIC_RUN",
    type=bool,
    default=True,
    show_default=True,
    help="True: stochastic outcomes simulations, False: continuous deterministic simulations",
)
@click.option(
    "--write-csv/--no-write-csv",
    default=False,
    show_default=True,
    help="write CSV output at end of simulation",
)
@click.option(
    "--write-parquet/--no-write-parquet",
    default=True,
    show_default=True,
    help="write parquet file output at end of simulation",
)
def simulate(
    config_file,
    in_run_id,
    in_prefix,
    out_run_id,
    out_prefix,
    scenarios_outcomes,
    nslots,
    jobs,
    first_sim_index,
    stoch_traj_flag,
    write_csv,
    write_parquet,
):
    spatial_path_prefix = ""
    config.clear()
    config.read(user=False)
    config.set_file(config_file)
    spatial_config = config["spatial_setup"]
    spatial_base_path = config["data_path"].get()
    spatial_base_path = pathlib.Path(spatial_path_prefix + spatial_base_path)

    if not scenarios_outcomes:
        scenarios_outcomes = config["outcomes"]["scenarios"].as_str_seq()
    print(f"Outcomes scenarios to be run: {', '.join(scenarios_outcomes)}")

    if not nslots:
        nslots = config["nslots"].as_number()
    print(f"Simulations to be run: {nslots}")

    spatial_setup = setup.SpatialSetup(
        setup_name=config["setup_name"].get(),
        geodata_file=spatial_base_path / spatial_config["geodata"].get(),
        mobility_file=spatial_base_path / spatial_config["mobility"].get()
        if spatial_config["mobility"].exists()
        else None,
        popnodes_key=spatial_config["popnodes"].get(),
        nodenames_key=spatial_config["nodenames"].get(),
    )

    start = time.monotonic()
    out_prefix_is_none = out_prefix is None
    for scenario_outcomes in scenarios_outcomes:
        print(f"outcome {scenario_outcomes}")

        if out_prefix_is_none:
            out_prefix = config["name"].get() + "/" + str(scenario_outcomes) + "/"
        if in_prefix is None:
            raise ValueError(f"in_prefix must be provided")
        s = setup.Setup(
            setup_name=config["name"].get() + "/" + str(scenarios_outcomes) + "/",
            spatial_setup=spatial_setup,
            nslots=nslots,
            outcomes_config=config["outcomes"],
            outcomes_scenario=scenario_outcomes,
            ti=config["start_date"].as_date(),
            tf=config["end_date"].as_date(),
            write_csv=write_csv,
            write_parquet=write_parquet,
            first_sim_index=first_sim_index,
            in_run_id=in_run_id,
            in_prefix=in_prefix,
            out_run_id=out_run_id,
            out_prefix=out_prefix,
            stoch_traj_flag=stoch_traj_flag,
        )

        outdir = file_paths.create_dir_name(out_run_id, out_prefix, "hosp")
        os.makedirs(outdir, exist_ok=True)

        print(
            f"""
>> Starting {nslots} model runs beginning from {first_sim_index} on {jobs} processes
>> Scenario: {scenario_outcomes} 
>> writing to folder : {out_prefix}
>> running ***{'STOCHASTIC' if stoch_traj_flag else 'DETERMINISTIC'}*** trajectories"""
        )

        if config["outcomes"]["method"].get() == "delayframe":
            outcomes.run_parallel_outcomes(sim_id2write=first_sim_index, s=s, nslots=nslots, n_jobs=jobs)
        else:
            raise ValueError(f"Only method 'delayframe' is supported at the moment.")

    print(f">> All runs completed in {time.monotonic() - start:.1f} seconds")


if __name__ == "__main__":
    simulate()

## @endcond
