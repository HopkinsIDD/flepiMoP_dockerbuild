import gempyor
import numpy as np
import pandas as pd
import datetime
import pytest

from gempyor.utils import config

import pandas as pd
import numpy as np
import datetime
import matplotlib.pyplot as plt
import glob, os, sys
from pathlib import Path

# import seaborn as sns
import pyarrow.parquet as pq
import pyarrow as pa
from gempyor import file_paths, setup, outcomes

config_path_prefix = ""  #'tests/outcomes/'

### To generate files for this test, see notebook Test Outcomes  playbook.ipynb in COVID19_Maryland

geoid = ["15005", "15007", "15009", "15001", "15003"]
diffI = np.arange(5) * 2
date_data = datetime.date(2020, 4, 15)
subclasses = ["_A", "_B"]

os.chdir(os.path.dirname(__file__))


def test_outcome_scenario():
    os.chdir(os.path.dirname(__file__))  ## this is redundant but necessary. Why ?
    inference_simulator = gempyor.InferenceSimulator(
        config_path=f"{config_path_prefix}config.yml",
        run_id=1,
        prefix="",
        first_sim_index=1,
        outcome_scenario="high_death_rate",
        stoch_traj_flag=False,
    )

    outcomes.onerun_delayframe_outcomes(sim_id2write=1, s=inference_simulator.s, load_ID=False)

    hosp = pq.read_table(f"{config_path_prefix}model_output/hosp/000000001.1.hosp.parquet").to_pandas()
    hosp.set_index("time", drop=True, inplace=True)
    for i, place in enumerate(geoid):
        for dt in hosp.index:
            if dt.date() == date_data:
                assert hosp[hosp["geoid"] == place]["incidI"][dt] == diffI[i]
                assert hosp[hosp["geoid"] == place]["incidH"][dt + datetime.timedelta(7)] == diffI[i] * 0.1
                assert hosp[hosp["geoid"] == place]["incidD"][dt + datetime.timedelta(2)] == diffI[i] * 0.01
                assert hosp[hosp["geoid"] == place]["incidICU"][dt + datetime.timedelta(7)] == diffI[i] * 0.1 * 0.4
                for j in range(7):
                    assert hosp[hosp["geoid"] == place]["hosp_curr"][dt + datetime.timedelta(7 + j)] == diffI[i] * 0.1
                assert hosp[hosp["geoid"] == place]["hosp_curr"][dt + datetime.timedelta(7 + 8)] == 0

            elif dt.date() < date_data:
                assert hosp[hosp["geoid"] == place]["incidH"][dt + datetime.timedelta(7)] == 0
                assert hosp[hosp["geoid"] == place]["incidI"][dt] == 0
                assert hosp[hosp["geoid"] == place]["incidD"][dt + datetime.timedelta(2)] == 0
                assert hosp[hosp["geoid"] == place]["incidICU"][dt + datetime.timedelta(7)] == 0
                assert hosp[hosp["geoid"] == place]["hosp_curr"][dt + datetime.timedelta(7)] == 0
            elif dt.date() > (date_data + datetime.timedelta(7)):
                assert hosp[hosp["geoid"] == place]["incidH"][dt] == 0
                assert hosp[hosp["geoid"] == place]["incidI"][dt - datetime.timedelta(7)] == 0
                assert hosp[hosp["geoid"] == place]["incidD"][dt - datetime.timedelta(4)] == 0
                assert hosp[hosp["geoid"] == place]["incidICU"][dt] == 0
    hpar = pq.read_table(f"{config_path_prefix}model_output/hpar/000000001.1.hpar.parquet").to_pandas()
    for i, place in enumerate(geoid):
        assert (
            float(
                hpar[(hpar["geoid"] == place) & (hpar["outcome"] == "incidH") & (hpar["quantity"] == "probability")][
                    "value"
                ]
            )
            == 0.1
        )
        assert (
            float(
                hpar[(hpar["geoid"] == place) & (hpar["outcome"] == "incidH") & (hpar["quantity"] == "delay")]["value"]
            )
            == 7
        )
        assert (
            float(
                hpar[(hpar["geoid"] == place) & (hpar["outcome"] == "incidH") & (hpar["quantity"] == "duration")][
                    "value"
                ]
            )
            == 7
        )
        assert (
            float(
                hpar[(hpar["geoid"] == place) & (hpar["outcome"] == "incidD") & (hpar["quantity"] == "probability")][
                    "value"
                ]
            )
            == 0.01
        )
        assert (
            float(
                hpar[(hpar["geoid"] == place) & (hpar["outcome"] == "incidD") & (hpar["quantity"] == "delay")]["value"]
            )
            == 2
        )
        assert (
            float(
                hpar[(hpar["geoid"] == place) & (hpar["outcome"] == "incidICU") & (hpar["quantity"] == "probability")][
                    "value"
                ]
            )
            == 0.4
        )
        assert (
            float(
                hpar[(hpar["geoid"] == place) & (hpar["outcome"] == "incidICU") & (hpar["quantity"] == "delay")][
                    "value"
                ]
            )
            == 0
        )


def test_outcome_scenario_with_load():
    os.chdir(os.path.dirname(__file__))
    inference_simulator = gempyor.InferenceSimulator(
        config_path=f"{config_path_prefix}config_load.yml",
        run_id=2,
        prefix="",
        first_sim_index=1,
        outcome_scenario="high_death_rate",
        stoch_traj_flag=False,
    )

    outcomes.onerun_delayframe_outcomes(sim_id2write=1, s=inference_simulator.s, load_ID=False)

    hpar_config = pq.read_table(f"{config_path_prefix}model_output/hpar/000000001.1.hpar.parquet").to_pandas()
    hpar_rel = pq.read_table(f"{config_path_prefix}model_output/hpar/000000001.2.hpar.parquet").to_pandas()

    for out in ["incidH", "incidD", "incidICU"]:
        for i, place in enumerate(geoid):
            a = hpar_rel[(hpar_rel["outcome"] == out) & (hpar_rel["geoid"] == place)]
            b = hpar_config[(hpar_rel["outcome"] == out) & (hpar_config["geoid"] == place)]
            assert len(a) == len(b)
            for j in range(len(a)):
                if b.iloc[j]["quantity"] in ["delay", "duration"]:
                    assert a.iloc[j]["value"] == b.iloc[j]["value"]
                else:  # probabiliy
                    if b.iloc[j]["outcome"] == "incidD":
                        assert a.iloc[j]["value"] == b.iloc[j]["value"] * 0.01
                    elif b.iloc[j]["outcome"] == "incidICU":
                        assert a.iloc[j]["value"] == b.iloc[j]["value"] * 0.4
                    elif b.iloc[j]["outcome"] == "incidH":
                        assert a.iloc[j]["value"] == b.iloc[j]["value"] * diffI[i] * 0.1


def test_outcomes_read_write_hpar():
    os.chdir(os.path.dirname(__file__))
    config.clear()
    config.read(user=False)

    inference_simulator = gempyor.InferenceSimulator(
        config_path=f"{config_path_prefix}config_load.yml",
        run_id=2,
        prefix="",
        first_sim_index=1,
        outcome_scenario="high_death_rate",
        stoch_traj_flag=False,
        out_run_id=3,
    )
    outcomes.onerun_delayframe_outcomes(sim_id2write=1, s=inference_simulator.s, load_ID=True, sim_id2load=1)

    hpar_read = pq.read_table(f"{config_path_prefix}model_output/hpar/000000001.2.hpar.parquet").to_pandas()
    hpar_wrote = pq.read_table(f"{config_path_prefix}model_output/hpar/000000001.3.hpar.parquet").to_pandas()
    assert (hpar_read == hpar_wrote).all().all()
    hnpi_read = pq.read_table(f"{config_path_prefix}model_output/hnpi/000000001.2.hnpi.parquet").to_pandas()
    hnpi_wrote = pq.read_table(f"{config_path_prefix}model_output/hnpi/000000001.3.hnpi.parquet").to_pandas()
    assert (hnpi_read == hnpi_wrote).all().all()
    hosp_read = pq.read_table(f"{config_path_prefix}model_output/hosp/000000001.2.hosp.parquet").to_pandas()
    hosp_wrote = pq.read_table(f"{config_path_prefix}model_output/hosp/000000001.3.hosp.parquet").to_pandas()
    assert (hosp_read == hosp_wrote).all().all()


def test_outcome_scenario_subclasses():
    os.chdir(os.path.dirname(__file__))

    inference_simulator = gempyor.InferenceSimulator(
        config_path=f"{config_path_prefix}config_subclasses.yml",
        run_id=1,
        prefix="",
        first_sim_index=1,
        outcome_scenario="high_death_rate",
        stoch_traj_flag=False,
        out_run_id=10,
    )

    outcomes.onerun_delayframe_outcomes(sim_id2write=1, s=inference_simulator.s)

    hosp = pq.read_table(f"{config_path_prefix}model_output/hosp/000000001.10.hosp.parquet").to_pandas()
    hosp.set_index("time", drop=True, inplace=True)

    for i, place in enumerate(geoid):
        for dt in hosp.index:
            if dt.date() == date_data:
                assert hosp[hosp["geoid"] == place]["incidI"][dt] == diffI[i]
                assert hosp[hosp["geoid"] == place]["incidH"][dt + datetime.timedelta(7)] == diffI[i] * 0.1 * len(
                    subclasses
                )
                assert hosp[hosp["geoid"] == place]["incidD"][dt + datetime.timedelta(2)] == diffI[i] * 0.01 * len(
                    subclasses
                )
                assert hosp[hosp["geoid"] == place]["incidICU"][dt + datetime.timedelta(7)] == diffI[
                    i
                ] * 0.1 * 0.4 * len(subclasses)
                for j in range(7):
                    assert hosp[hosp["geoid"] == place]["hosp_curr"][dt + datetime.timedelta(7 + j)] == diffI[
                        i
                    ] * 0.1 * len(subclasses)
                assert hosp[hosp["geoid"] == place]["hosp_curr"][dt + datetime.timedelta(7 + 8)] == 0

            elif dt.date() < date_data:
                assert hosp[hosp["geoid"] == place]["incidH"][dt + datetime.timedelta(7)] == 0
                assert hosp[hosp["geoid"] == place]["incidI"][dt] == 0
                assert hosp[hosp["geoid"] == place]["incidD"][dt + datetime.timedelta(2)] == 0
                assert hosp[hosp["geoid"] == place]["incidICU"][dt + datetime.timedelta(7)] == 0
                assert hosp[hosp["geoid"] == place]["hosp_curr"][dt + datetime.timedelta(7)] == 0
            elif dt.date() > (date_data + datetime.timedelta(7)):
                assert hosp[hosp["geoid"] == place]["incidH"][dt] == 0
                assert hosp[hosp["geoid"] == place]["incidI"][dt - datetime.timedelta(7)] == 0
                assert hosp[hosp["geoid"] == place]["incidD"][dt - datetime.timedelta(4)] == 0
                assert hosp[hosp["geoid"] == place]["incidICU"][dt] == 0

    for cl in subclasses:
        for i, place in enumerate(geoid):
            for dt in hosp.index:
                if dt.date() == date_data:
                    assert hosp[hosp["geoid"] == place][f"incidH{cl}"][dt + datetime.timedelta(7)] == diffI[i] * 0.1
                    assert hosp[hosp["geoid"] == place][f"incidD{cl}"][dt + datetime.timedelta(2)] == diffI[i] * 0.01
                    assert (
                        hosp[hosp["geoid"] == place][f"incidICU{cl}"][dt + datetime.timedelta(7)]
                        == diffI[i] * 0.1 * 0.4
                    )
                    for j in range(7):
                        assert (
                            hosp[hosp["geoid"] == place][f"hosp_curr{cl}"][dt + datetime.timedelta(7 + j)]
                            == diffI[i] * 0.1
                        )
                    assert hosp[hosp["geoid"] == place][f"hosp_curr{cl}"][dt + datetime.timedelta(7 + 8)] == 0

                elif dt.date() < date_data:
                    assert hosp[hosp["geoid"] == place][f"incidH{cl}"][dt + datetime.timedelta(7)] == 0
                    assert hosp[hosp["geoid"] == place][f"incidD{cl}"][dt + datetime.timedelta(2)] == 0
                    assert hosp[hosp["geoid"] == place][f"incidICU{cl}"][dt + datetime.timedelta(7)] == 0
                    assert hosp[hosp["geoid"] == place][f"hosp_curr{cl}"][dt + datetime.timedelta(7)] == 0
                elif dt.date() > (date_data + datetime.timedelta(7)):
                    assert hosp[hosp["geoid"] == place][f"incidH{cl}"][dt] == 0
                    assert hosp[hosp["geoid"] == place][f"incidD{cl}"][dt - datetime.timedelta(4)] == 0
                    assert hosp[hosp["geoid"] == place][f"incidICU{cl}"][dt] == 0

    hpar = pq.read_table(f"{config_path_prefix}model_output/hpar/000000001.10.hpar.parquet").to_pandas()
    for cl in subclasses:
        for i, place in enumerate(geoid):
            assert (
                float(
                    hpar[
                        (hpar["geoid"] == place)
                        & (hpar["outcome"] == f"incidH{cl}")
                        & (hpar["quantity"] == "probability")
                    ]["value"]
                )
                == 0.1
            )
            assert (
                float(
                    hpar[(hpar["geoid"] == place) & (hpar["outcome"] == f"incidH{cl}") & (hpar["quantity"] == "delay")][
                        "value"
                    ]
                )
                == 7
            )
            assert (
                float(
                    hpar[
                        (hpar["geoid"] == place) & (hpar["outcome"] == f"incidH{cl}") & (hpar["quantity"] == "duration")
                    ]["value"]
                )
                == 7
            )
            assert (
                float(
                    hpar[
                        (hpar["geoid"] == place)
                        & (hpar["outcome"] == f"incidD{cl}")
                        & (hpar["quantity"] == "probability")
                    ]["value"]
                )
                == 0.01
            )
            assert (
                float(
                    hpar[(hpar["geoid"] == place) & (hpar["outcome"] == f"incidD{cl}") & (hpar["quantity"] == "delay")][
                        "value"
                    ]
                )
                == 2
            )
            assert (
                float(
                    hpar[
                        (hpar["geoid"] == place)
                        & (hpar["outcome"] == f"incidICU{cl}")
                        & (hpar["quantity"] == "probability")
                    ]["value"]
                )
                == 0.4
            )
            assert (
                float(
                    hpar[
                        (hpar["geoid"] == place) & (hpar["outcome"] == f"incidICU{cl}") & (hpar["quantity"] == "delay")
                    ]["value"]
                )
                == 0
            )
            # assert((hpar[(hpar['geoid']== place) & (hpar['outcome']== f'incidICU{cl}')]['source'] == f'incidH{cl}').all())
            # assert((hpar[(hpar['geoid']== place) & (hpar['outcome']== f'incidH{cl}')]['source'] == f'incidI').all())


def test_outcome_scenario_with_load_subclasses():
    os.chdir(os.path.dirname(__file__))

    inference_simulator = gempyor.InferenceSimulator(
        config_path=f"{config_path_prefix}config_load_subclasses.yml",
        run_id=1,
        prefix="",
        first_sim_index=1,
        outcome_scenario="high_death_rate",
        stoch_traj_flag=False,
        out_run_id=11,
    )

    outcomes.onerun_delayframe_outcomes(sim_id2write=1, s=inference_simulator.s)

    hpar_config = pq.read_table(f"{config_path_prefix}model_output/hpar/000000001.10.hpar.parquet").to_pandas()
    hpar_rel = pq.read_table(f"{config_path_prefix}model_output/hpar/000000001.11.hpar.parquet").to_pandas()
    for cl in subclasses:
        for out in [f"incidH{cl}", f"incidD{cl}", f"incidICU{cl}"]:
            for i, place in enumerate(geoid):
                a = hpar_rel[(hpar_rel["outcome"] == out) & (hpar_rel["geoid"] == place)]
                b = hpar_config[(hpar_rel["outcome"] == out) & (hpar_config["geoid"] == place)]
                assert len(a) == len(b)
                for j in range(len(a)):
                    if b.iloc[j]["quantity"] in ["delay", "duration"]:
                        assert a.iloc[j]["value"] == b.iloc[j]["value"]
                    else:  # probabiliy
                        if cl == "_A":
                            add = 0.05
                        elif cl == "_B":
                            add = 0.075

                        if b.iloc[j]["outcome"] == f"incidD{cl}":
                            assert a.iloc[j]["value"] == b.iloc[j]["value"] * 0.01
                        elif b.iloc[j]["outcome"] == f"incidICU{cl}":
                            assert a.iloc[j]["value"] == b.iloc[j]["value"] * 0.4
                        elif b.iloc[j]["outcome"] == f"incidH{cl}":
                            assert a.iloc[j]["value"] == b.iloc[j]["value"] * (diffI[i] * 0.1 + add)

    hosp_rel = pq.read_table(f"{config_path_prefix}model_output/hosp/000000001.11.hosp.parquet").to_pandas()
    assert (hosp_rel["incidH"] == hosp_rel["incidH_A"] + hosp_rel["incidH_B"]).all()


def test_outcomes_read_write_hpar_subclasses():
    os.chdir(os.path.dirname(__file__))

    inference_simulator = gempyor.InferenceSimulator(
        config_path=f"{config_path_prefix}config_load.yml",
        run_id=1,
        prefix="",
        first_sim_index=1,
        outcome_scenario="high_death_rate",
        stoch_traj_flag=False,
        out_run_id=12,
    )

    outcomes.onerun_delayframe_outcomes(sim_id2write=1, s=inference_simulator.s)

    inference_simulator = gempyor.InferenceSimulator(
        config_path=f"{config_path_prefix}config_load.yml",
        run_id=12,
        prefix="",
        first_sim_index=1,
        outcome_scenario="high_death_rate",
        stoch_traj_flag=False,
        out_run_id=13,
    )

    outcomes.onerun_delayframe_outcomes(sim_id2write=1, s=inference_simulator.s, load_ID=True, sim_id2load=1)

    hpar_read = pq.read_table(f"{config_path_prefix}model_output/hpar/000000001.12.hpar.parquet").to_pandas()
    hpar_wrote = pq.read_table(f"{config_path_prefix}model_output/hpar/000000001.13.hpar.parquet").to_pandas()
    assert (hpar_read == hpar_wrote).all().all()

    hosp_read = pq.read_table(f"{config_path_prefix}model_output/hosp/000000001.12.hosp.parquet").to_pandas()
    hosp_wrote = pq.read_table(f"{config_path_prefix}model_output/hosp/000000001.13.hosp.parquet").to_pandas()
    assert (hosp_read == hosp_wrote).all().all()


def test_multishift_notstochdelays():
    os.chdir(os.path.dirname(__file__))
    shp = (10, 2)  # dateXplace
    array = np.array(
        [
            [28, 39],
            [24, 16],
            [11, 24],
            [19, 32],
            [4, 30],
            [11, 28],
            [35, 6],
            [25, 3],
            [12, 3],
            [36, 29],
        ]
    )
    shifts = np.array([[1, 0], [2, 1], [1, 0], [2, 2], [1, 2], [0, 1], [1, 1], [1, 2], [1, 2], [1, 0]])
    expected = np.array(
        [
            [0, 39],
            [28, 0],
            [0, 40],
            [35, 0],
            [0, 0],
            [34, 32],
            [0, 58],
            [35, 6],
            [25, 0],
            [12, 32],
        ]
    )
    assert (outcomes.multishift(array, shifts, stoch_delay_flag=False) == expected).all()


def test_outcomes_npi():
    os.chdir(os.path.dirname(__file__))

    inference_simulator = gempyor.InferenceSimulator(
        config_path=f"{config_path_prefix}config_npi.yml",
        run_id=1,
        prefix="",
        first_sim_index=1,
        outcome_scenario="high_death_rate",
        stoch_traj_flag=False,
        out_run_id=105,
    )
    outcomes.onerun_delayframe_outcomes(sim_id2write=1, s=inference_simulator.s)

    hosp = pq.read_table(f"{config_path_prefix}model_output/hosp/000000001.105.hosp.parquet").to_pandas()
    hosp.set_index("time", drop=True, inplace=True)
    # same as config.yaml (doubled, then NPI halve it)
    for i, place in enumerate(geoid):
        for dt in hosp.index:
            if dt.date() == date_data:
                assert hosp[hosp["geoid"] == place]["incidI"][dt] == diffI[i]
                assert hosp[hosp["geoid"] == place]["incidH"][dt + datetime.timedelta(7)] == diffI[i] * 0.1
                assert hosp[hosp["geoid"] == place]["incidD"][dt + datetime.timedelta(2)] == diffI[i] * 0.01
                assert hosp[hosp["geoid"] == place]["incidICU"][dt + datetime.timedelta(7)] == diffI[i] * 0.1 * 0.4
                for j in range(7):
                    assert hosp[hosp["geoid"] == place]["hosp_curr"][dt + datetime.timedelta(7 + j)] == diffI[i] * 0.1
                assert hosp[hosp["geoid"] == place]["hosp_curr"][dt + datetime.timedelta(7 + 8)] == 0

            elif dt.date() < date_data:
                assert hosp[hosp["geoid"] == place]["incidH"][dt + datetime.timedelta(7)] == 0
                assert hosp[hosp["geoid"] == place]["incidI"][dt] == 0
                assert hosp[hosp["geoid"] == place]["incidD"][dt + datetime.timedelta(2)] == 0
                assert hosp[hosp["geoid"] == place]["incidICU"][dt + datetime.timedelta(7)] == 0
                assert hosp[hosp["geoid"] == place]["hosp_curr"][dt + datetime.timedelta(7)] == 0
            elif dt.date() > (date_data + datetime.timedelta(7)):
                assert hosp[hosp["geoid"] == place]["incidH"][dt] == 0
                assert hosp[hosp["geoid"] == place]["incidI"][dt - datetime.timedelta(7)] == 0
                assert hosp[hosp["geoid"] == place]["incidD"][dt - datetime.timedelta(4)] == 0
                assert hosp[hosp["geoid"] == place]["incidICU"][dt] == 0
    hpar = pq.read_table(f"{config_path_prefix}model_output/hpar/000000001.105.hpar.parquet").to_pandas()
    # Doubled everything from previous config.yaml
    for i, place in enumerate(geoid):
        assert (
            float(
                hpar[(hpar["geoid"] == place) & (hpar["outcome"] == "incidH") & (hpar["quantity"] == "probability")][
                    "value"
                ]
            )
            == 0.1 * 2
        )
        assert (
            float(
                hpar[(hpar["geoid"] == place) & (hpar["outcome"] == "incidH") & (hpar["quantity"] == "delay")]["value"]
            )
            == 7 * 2
        )
        assert (
            float(
                hpar[(hpar["geoid"] == place) & (hpar["outcome"] == "incidH") & (hpar["quantity"] == "duration")][
                    "value"
                ]
            )
            == 7 * 2
        )
        assert (
            float(
                hpar[(hpar["geoid"] == place) & (hpar["outcome"] == "incidD") & (hpar["quantity"] == "probability")][
                    "value"
                ]
            )
            == 0.01 * 2
        )
        assert (
            float(
                hpar[(hpar["geoid"] == place) & (hpar["outcome"] == "incidD") & (hpar["quantity"] == "delay")]["value"]
            )
            == 2 * 2
        )
        assert (
            float(
                hpar[(hpar["geoid"] == place) & (hpar["outcome"] == "incidICU") & (hpar["quantity"] == "probability")][
                    "value"
                ]
            )
            == 0.4 * 2
        )
        assert (
            float(
                hpar[(hpar["geoid"] == place) & (hpar["outcome"] == "incidICU") & (hpar["quantity"] == "delay")][
                    "value"
                ]
            )
            == 0 * 2
        )


def test_outcomes_read_write_hnpi():
    os.chdir(os.path.dirname(__file__))

    inference_simulator = gempyor.InferenceSimulator(
        config_path=f"{config_path_prefix}config_npi.yml",
        run_id=105,
        prefix="",
        first_sim_index=1,
        outcome_scenario="high_death_rate",
        stoch_traj_flag=False,
        out_run_id=106,
    )

    outcomes.onerun_delayframe_outcomes(sim_id2write=1, s=inference_simulator.s, load_ID=True, sim_id2load=1)

    hpar_read = pq.read_table(f"{config_path_prefix}model_output/hpar/000000001.105.hpar.parquet").to_pandas()
    hpar_wrote = pq.read_table(f"{config_path_prefix}model_output/hpar/000000001.106.hpar.parquet").to_pandas()
    assert (hpar_read == hpar_wrote).all().all()
    hnpi_read = pq.read_table(f"{config_path_prefix}model_output/hnpi/000000001.105.hnpi.parquet").to_pandas()
    hnpi_wrote = pq.read_table(f"{config_path_prefix}model_output/hnpi/000000001.106.hnpi.parquet").to_pandas()

    assert (hnpi_read == hnpi_wrote).all().all()
    hosp_read = pq.read_table(f"{config_path_prefix}model_output/hosp/000000001.105.hosp.parquet").to_pandas()
    hosp_wrote = pq.read_table(f"{config_path_prefix}model_output/hosp/000000001.106.hosp.parquet").to_pandas()
    assert (hosp_read == hosp_wrote).all().all()


def test_outcomes_read_write_hnpi2():
    os.chdir(os.path.dirname(__file__))

    inference_simulator = gempyor.InferenceSimulator(
        config_path=f"{config_path_prefix}config_npi.yml",
        run_id=105,
        prefix="",
        first_sim_index=1,
        outcome_scenario="high_death_rate",
        stoch_traj_flag=False,
        out_run_id=106,
    )

    hnpi_read = pq.read_table(f"{config_path_prefix}model_output/hnpi/000000001.105.hnpi.parquet").to_pandas()
    hnpi_read["reduction"] = np.random.random(len(hnpi_read)) * 2 - 1
    out_hnpi = pa.Table.from_pandas(hnpi_read, preserve_index=False)
    pa.parquet.write_table(out_hnpi, file_paths.create_file_name(105, "", 1, "hnpi", "parquet"))
    import random

    random.seed(10)
    outcomes.onerun_delayframe_outcomes(sim_id2write=1, s=inference_simulator.s, load_ID=True, sim_id2load=1)

    hnpi_read = pq.read_table(f"{config_path_prefix}model_output/hnpi/000000001.105.hnpi.parquet").to_pandas()
    hnpi_wrote = pq.read_table(f"{config_path_prefix}model_output/hnpi/000000001.106.hnpi.parquet").to_pandas()
    assert (hnpi_read == hnpi_wrote).all().all()

    # runs with the new, random NPI
    inference_simulator = gempyor.InferenceSimulator(
        config_path=f"{config_path_prefix}config_npi.yml",
        run_id=106,
        prefix="",
        first_sim_index=1,
        outcome_scenario="high_death_rate",
        stoch_traj_flag=False,
        out_run_id=107,
    )
    outcomes.onerun_delayframe_outcomes(sim_id2write=1, s=inference_simulator.s, load_ID=True, sim_id2load=1)

    hpar_read = pq.read_table(f"{config_path_prefix}model_output/hpar/000000001.106.hpar.parquet").to_pandas()
    hpar_wrote = pq.read_table(f"{config_path_prefix}model_output/hpar/000000001.107.hpar.parquet").to_pandas()
    assert (hpar_read == hpar_wrote).all().all()
    hnpi_read = pq.read_table(f"{config_path_prefix}model_output/hnpi/000000001.106.hnpi.parquet").to_pandas()
    hnpi_wrote = pq.read_table(f"{config_path_prefix}model_output/hnpi/000000001.107.hnpi.parquet").to_pandas()
    assert (hnpi_read == hnpi_wrote).all().all()
    hosp_read = pq.read_table(f"{config_path_prefix}model_output/hosp/000000001.106.hosp.parquet").to_pandas()
    hosp_wrote = pq.read_table(f"{config_path_prefix}model_output/hosp/000000001.107.hosp.parquet").to_pandas()
    assert (hosp_read == hosp_wrote).all().all()


def test_outcomes_npi_custom_pname():
    os.chdir(os.path.dirname(__file__))

    inference_simulator = gempyor.InferenceSimulator(
        config_path=f"{config_path_prefix}config_npi_custom_pnames.yml",
        run_id=1,
        prefix="",
        first_sim_index=1,
        outcome_scenario="high_death_rate",
        stoch_traj_flag=False,
        out_run_id=105,
    )
    outcomes.onerun_delayframe_outcomes(sim_id2write=1, s=inference_simulator.s, load_ID=False, sim_id2load=1)

    hosp = pq.read_table(f"{config_path_prefix}model_output/hosp/000000001.105.hosp.parquet").to_pandas()
    hosp.set_index("time", drop=True, inplace=True)
    # same as config.yaml (doubled, then NPI halve it)
    for i, place in enumerate(geoid):
        for dt in hosp.index:
            if dt.date() == date_data:
                assert hosp[hosp["geoid"] == place]["incidI"][dt] == diffI[i]
                assert hosp[hosp["geoid"] == place]["incidH"][dt + datetime.timedelta(7)] == diffI[i] * 0.1
                assert hosp[hosp["geoid"] == place]["incidD"][dt + datetime.timedelta(2)] == diffI[i] * 0.01
                assert hosp[hosp["geoid"] == place]["incidICU"][dt + datetime.timedelta(7)] == diffI[i] * 0.1 * 0.4
                for j in range(7):
                    assert hosp[hosp["geoid"] == place]["hosp_curr"][dt + datetime.timedelta(7 + j)] == diffI[i] * 0.1
                assert hosp[hosp["geoid"] == place]["hosp_curr"][dt + datetime.timedelta(7 + 8)] == 0

            elif dt.date() < date_data:
                assert hosp[hosp["geoid"] == place]["incidH"][dt + datetime.timedelta(7)] == 0
                assert hosp[hosp["geoid"] == place]["incidI"][dt] == 0
                assert hosp[hosp["geoid"] == place]["incidD"][dt + datetime.timedelta(2)] == 0
                assert hosp[hosp["geoid"] == place]["incidICU"][dt + datetime.timedelta(7)] == 0
                assert hosp[hosp["geoid"] == place]["hosp_curr"][dt + datetime.timedelta(7)] == 0
            elif dt.date() > (date_data + datetime.timedelta(7)):
                assert hosp[hosp["geoid"] == place]["incidH"][dt] == 0
                assert hosp[hosp["geoid"] == place]["incidI"][dt - datetime.timedelta(7)] == 0
                assert hosp[hosp["geoid"] == place]["incidD"][dt - datetime.timedelta(4)] == 0
                assert hosp[hosp["geoid"] == place]["incidICU"][dt] == 0
    hpar = pq.read_table(f"{config_path_prefix}model_output/hpar/000000001.105.hpar.parquet").to_pandas()
    # Doubled everything from previous config.yaml
    for i, place in enumerate(geoid):
        assert (
            float(
                hpar[(hpar["geoid"] == place) & (hpar["outcome"] == "incidH") & (hpar["quantity"] == "probability")][
                    "value"
                ]
            )
            == 0.1 * 2
        )
        assert (
            float(
                hpar[(hpar["geoid"] == place) & (hpar["outcome"] == "incidH") & (hpar["quantity"] == "delay")]["value"]
            )
            == 7 * 2
        )
        assert (
            float(
                hpar[(hpar["geoid"] == place) & (hpar["outcome"] == "incidH") & (hpar["quantity"] == "duration")][
                    "value"
                ]
            )
            == 7 * 2
        )
        assert (
            float(
                hpar[(hpar["geoid"] == place) & (hpar["outcome"] == "incidD") & (hpar["quantity"] == "probability")][
                    "value"
                ]
            )
            == 0.01 * 2
        )
        assert (
            float(
                hpar[(hpar["geoid"] == place) & (hpar["outcome"] == "incidD") & (hpar["quantity"] == "delay")]["value"]
            )
            == 2 * 2
        )
        assert (
            float(
                hpar[(hpar["geoid"] == place) & (hpar["outcome"] == "incidICU") & (hpar["quantity"] == "probability")][
                    "value"
                ]
            )
            == 0.4 * 2
        )
        assert (
            float(
                hpar[(hpar["geoid"] == place) & (hpar["outcome"] == "incidICU") & (hpar["quantity"] == "delay")][
                    "value"
                ]
            )
            == 0 * 2
        )


def test_outcomes_read_write_hnpi_custom_pname():
    os.chdir(os.path.dirname(__file__))

    inference_simulator = gempyor.InferenceSimulator(
        config_path=f"{config_path_prefix}config_npi_custom_pnames.yml",
        run_id=105,
        prefix="",
        first_sim_index=1,
        outcome_scenario="high_death_rate",
        stoch_traj_flag=False,
        out_run_id=106,
    )

    outcomes.onerun_delayframe_outcomes(sim_id2write=1, s=inference_simulator.s, load_ID=True, sim_id2load=1)

    hpar_read = pq.read_table(f"{config_path_prefix}model_output/hpar/000000001.105.hpar.parquet").to_pandas()
    hpar_wrote = pq.read_table(f"{config_path_prefix}model_output/hpar/000000001.106.hpar.parquet").to_pandas()
    assert (hpar_read == hpar_wrote).all().all()
    hnpi_read = pq.read_table(f"{config_path_prefix}model_output/hnpi/000000001.105.hnpi.parquet").to_pandas()
    hnpi_wrote = pq.read_table(f"{config_path_prefix}model_output/hnpi/000000001.106.hnpi.parquet").to_pandas()
    assert (hnpi_read == hnpi_wrote).all().all()
    hosp_read = pq.read_table(f"{config_path_prefix}model_output/hosp/000000001.105.hosp.parquet").to_pandas()
    hosp_wrote = pq.read_table(f"{config_path_prefix}model_output/hosp/000000001.106.hosp.parquet").to_pandas()
    assert (hosp_read == hosp_wrote).all().all()


def test_outcomes_read_write_hnpi2_custom_pname():
    os.chdir(os.path.dirname(__file__))

    prefix = ""

    hnpi_read = pq.read_table(f"{config_path_prefix}model_output/hnpi/000000001.105.hnpi.parquet").to_pandas()
    hnpi_read["reduction"] = np.random.random(len(hnpi_read)) * 2 - 1
    out_hnpi = pa.Table.from_pandas(hnpi_read, preserve_index=False)
    pa.parquet.write_table(out_hnpi, file_paths.create_file_name(105, prefix, 1, "hnpi", "parquet"))
    import random

    random.seed(10)

    inference_simulator = gempyor.InferenceSimulator(
        config_path=f"{config_path_prefix}config_npi_custom_pnames.yml",
        run_id=105,
        prefix="",
        first_sim_index=1,
        outcome_scenario="high_death_rate",
        stoch_traj_flag=False,
        out_run_id=106,
    )

    outcomes.onerun_delayframe_outcomes(sim_id2write=1, s=inference_simulator.s, load_ID=True, sim_id2load=1)

    hnpi_read = pq.read_table(f"{config_path_prefix}model_output/hnpi/000000001.105.hnpi.parquet").to_pandas()
    hnpi_wrote = pq.read_table(f"{config_path_prefix}model_output/hnpi/000000001.106.hnpi.parquet").to_pandas()
    assert (hnpi_read == hnpi_wrote).all().all()

    # runs with the new, random NPI
    inference_simulator = gempyor.InferenceSimulator(
        config_path=f"{config_path_prefix}config_npi_custom_pnames.yml",
        run_id=106,
        prefix="",
        first_sim_index=1,
        outcome_scenario="high_death_rate",
        stoch_traj_flag=False,
        out_run_id=107,
    )

    outcomes.onerun_delayframe_outcomes(sim_id2write=1, s=inference_simulator.s, load_ID=True, sim_id2load=1)

    hpar_read = pq.read_table(f"{config_path_prefix}model_output/hpar/000000001.106.hpar.parquet").to_pandas()
    hpar_wrote = pq.read_table(f"{config_path_prefix}model_output/hpar/000000001.107.hpar.parquet").to_pandas()
    assert (hpar_read == hpar_wrote).all().all()
    hnpi_read = pq.read_table(f"{config_path_prefix}model_output/hnpi/000000001.106.hnpi.parquet").to_pandas()
    hnpi_wrote = pq.read_table(f"{config_path_prefix}model_output/hnpi/000000001.107.hnpi.parquet").to_pandas()
    assert (hnpi_read == hnpi_wrote).all().all()
    hosp_read = pq.read_table(f"{config_path_prefix}model_output/hosp/000000001.106.hosp.parquet").to_pandas()
    hosp_wrote = pq.read_table(f"{config_path_prefix}model_output/hosp/000000001.107.hosp.parquet").to_pandas()
    assert (hosp_read == hosp_wrote).all().all()


def test_outcomes_pcomp():
    os.chdir(os.path.dirname(__file__))
    prefix = ""

    inference_simulator = gempyor.InferenceSimulator(
        config_path=f"{config_path_prefix}config_mc_selection.yml",
        run_id=110,
        prefix="",
        first_sim_index=1,
        outcome_scenario="high_death_rate",
        stoch_traj_flag=False,
        out_run_id=111,
    )
    p_compmult = [1, 3]

    seir = pq.read_table(f"{config_path_prefix}model_output/seir/000000001.105.seir.parquet").to_pandas()
    seir2 = seir.copy()
    seir2["mc_vaccination_stage"] = "first_dose"
    for pl in geoid:
        seir2[pl] = seir2[pl] * p_compmult[1]
    new_seir = pd.concat([seir, seir2])
    out_df = pa.Table.from_pandas(new_seir, preserve_index=False)
    pa.parquet.write_table(out_df, file_paths.create_file_name(110, prefix, 1, "seir", "parquet"))
    outcomes.onerun_delayframe_outcomes(sim_id2write=1, s=inference_simulator.s, load_ID=False)

    hosp_f = pq.read_table(f"{config_path_prefix}model_output/hosp/000000001.111.hosp.parquet").to_pandas()
    hosp_f.set_index("time", drop=True, inplace=True)
    # same as config.yaml (doubled, then NPI halve it)
    for k, p_comp in enumerate(["0dose", "1dose"]):
        hosp = hosp_f
        for i, place in enumerate(geoid):
            for dt in hosp.index:
                if dt.date() == date_data:
                    assert hosp[hosp["geoid"] == place][f"incidI_{p_comp}"][dt] == diffI[i] * p_compmult[k]
                    assert (
                        hosp[hosp["geoid"] == place][f"incidH_{p_comp}"][dt + datetime.timedelta(7)]
                        - diffI[i] * 0.1 * p_compmult[k]
                        < 1e-8
                    )
                    assert (
                        hosp[hosp["geoid"] == place][f"incidD_{p_comp}"][dt + datetime.timedelta(2)]
                        - diffI[i] * 0.01 * p_compmult[k]
                        < 1e-8
                    )
                    assert (
                        hosp[hosp["geoid"] == place][f"incidICU_{p_comp}"][dt + datetime.timedelta(7)]
                        - diffI[i] * 0.1 * 0.4 * p_compmult[k]
                        < 1e-8
                    )
                    for j in range(7):
                        assert (
                            hosp[hosp["geoid"] == place][f"incidH_{p_comp}_curr"][dt + datetime.timedelta(7 + j)]
                            - diffI[i] * 0.1 * p_compmult[k]
                            < 1e-8
                        )
                    assert hosp[hosp["geoid"] == place][f"incidH_{p_comp}_curr"][dt + datetime.timedelta(7 + 8)] == 0

                elif dt.date() < date_data:
                    assert hosp[hosp["geoid"] == place][f"incidH_{p_comp}"][dt + datetime.timedelta(7)] == 0
                    assert hosp[hosp["geoid"] == place][f"incidI_{p_comp}"][dt] == 0
                    assert hosp[hosp["geoid"] == place][f"incidD_{p_comp}"][dt + datetime.timedelta(2)] == 0
                    assert hosp[hosp["geoid"] == place][f"incidICU_{p_comp}"][dt + datetime.timedelta(7)] == 0
                    assert hosp[hosp["geoid"] == place][f"incidH_{p_comp}_curr"][dt + datetime.timedelta(7)] == 0
                elif dt.date() > (date_data + datetime.timedelta(7)):
                    assert hosp[hosp["geoid"] == place][f"incidH_{p_comp}"][dt] == 0
                    assert hosp[hosp["geoid"] == place][f"incidI_{p_comp}"][dt - datetime.timedelta(7)] == 0
                    assert hosp[hosp["geoid"] == place][f"incidD_{p_comp}"][dt - datetime.timedelta(4)] == 0
                    assert hosp[hosp["geoid"] == place][f"incidICU_{p_comp}"][dt] == 0
    hpar_f = pq.read_table(f"{config_path_prefix}model_output/hpar/000000001.111.hpar.parquet").to_pandas()
    # Doubled everything from previous config.yaml
    # for k, p_comp in enumerate(["unvaccinated", "first_dose"]):
    for k, p_comp in enumerate(["0dose", "1dose"]):
        hpar = hpar_f
        for i, place in enumerate(geoid):
            assert (
                float(
                    hpar[
                        (hpar["geoid"] == place)
                        & (hpar["outcome"] == f"incidH_{p_comp}")
                        & (hpar["quantity"] == "probability")
                    ]["value"]
                )
                == 0.1 * 2
            )
            assert (
                float(
                    hpar[
                        (hpar["geoid"] == place)
                        & (hpar["outcome"] == f"incidH_{p_comp}")
                        & (hpar["quantity"] == "delay")
                    ]["value"]
                )
                == 7 * 2
            )
            assert (
                float(
                    hpar[
                        (hpar["geoid"] == place)
                        & (hpar["outcome"] == f"incidH_{p_comp}")
                        & (hpar["quantity"] == "duration")
                    ]["value"]
                )
                == 7 * 2
            )
            assert (
                float(
                    hpar[
                        (hpar["geoid"] == place)
                        & (hpar["outcome"] == f"incidD_{p_comp}")
                        & (hpar["quantity"] == "probability")
                    ]["value"]
                )
                == 0.01 * 2
            )
            assert (
                float(
                    hpar[
                        (hpar["geoid"] == place)
                        & (hpar["outcome"] == f"incidD_{p_comp}")
                        & (hpar["quantity"] == "delay")
                    ]["value"]
                )
                == 2 * 2
            )
            assert (
                float(
                    hpar[
                        (hpar["geoid"] == place)
                        & (hpar["outcome"] == f"incidICU_{p_comp}")
                        & (hpar["quantity"] == "probability")
                    ]["value"]
                )
                == 0.4 * 2
            )
            assert (
                float(
                    hpar[
                        (hpar["geoid"] == place)
                        & (hpar["outcome"] == f"incidICU_{p_comp}")
                        & (hpar["quantity"] == "delay")
                    ]["value"]
                )
                == 0 * 2
            )


def test_outcomes_pcomp_read_write():
    os.chdir(os.path.dirname(__file__))

    inference_simulator = gempyor.InferenceSimulator(
        config_path=f"{config_path_prefix}config_mc_selection.yml",
        run_id=111,
        prefix="",
        first_sim_index=1,
        outcome_scenario="high_death_rate",
        stoch_traj_flag=False,
        out_run_id=112,
    )

    outcomes.onerun_delayframe_outcomes(sim_id2write=1, s=inference_simulator.s, load_ID=True, sim_id2load=1)

    hpar_read = pq.read_table(f"{config_path_prefix}model_output/hpar/000000001.111.hpar.parquet").to_pandas()
    hpar_wrote = pq.read_table(f"{config_path_prefix}model_output/hpar/000000001.112.hpar.parquet").to_pandas()
    assert (hpar_read == hpar_wrote).all().all()
    hnpi_read = pq.read_table(f"{config_path_prefix}model_output/hnpi/000000001.111.hnpi.parquet").to_pandas()
    hnpi_wrote = pq.read_table(f"{config_path_prefix}model_output/hnpi/000000001.112.hnpi.parquet").to_pandas()
    assert (hnpi_read == hnpi_wrote).all().all()
    hosp_read = pq.read_table(f"{config_path_prefix}model_output/hosp/000000001.111.hosp.parquet").to_pandas()
    hosp_wrote = pq.read_table(f"{config_path_prefix}model_output/hosp/000000001.112.hosp.parquet").to_pandas()
    assert (hosp_read == hosp_wrote).all().all()


# ADD A test that everything is equivalent
