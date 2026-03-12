from typing import Literal, List, Dict
from power_grid_model.utils import json_deserialize_from_file
from power_grid_model import (
    CalculationMethod,
    ComponentType,
    DatasetType,
    MeasuredTerminalType,
    PowerGridModel,
    initialize_array,
    AngleMeasurementType,
)
from pathlib import Path
from modules.utils import find_max_id
from modules.utils import get_component_indices
from modules.h_matrix_gen import HMatrixGenerator
import numpy as np


class SEInputMaker:
    def __init__(
        self,
        network_name: Literal["cigre_mv", "cigre_lv"],
        sensor_setting: Literal["from_pq", "to_pq", "from_i", "to_i"],
        voltage_sensor_id: List[int] = None,
        u_sigma: float = None,
        u_rated_general: float = None,
        switch_status: List[int] = None,
        switch_index: List[int] = None,
        p_sigma: float = None,
        q_sigma: float = None,
        i_sigma: float = None,
        i_rated_general: float = None,
        general_seed: int = 42,
    ):
        self.network_name = network_name
        self.sensor_setting = sensor_setting
        self.voltage_sensor_id = voltage_sensor_id
        self.n_voltage_sensors = len(voltage_sensor_id)
        self._load_network()
        self._get_voltage_sensor_index()
        self.switch_status = switch_status
        self.switch_index = switch_index
        if switch_status is not None:
            self._change_switch_status()
        # sigma and rated general
        self.u_sigma = u_sigma
        self.u_angle_sigma = u_sigma / u_rated_general * 2 * np.pi
        self.u_rated_general = u_rated_general
        self.p_sigma = p_sigma
        self.q_sigma = q_sigma
        self.i_sigma = i_sigma
        self.i_rated_general = i_rated_general
        # number of components
        self.n_lines = len(self.input_data[ComponentType.line])
        self.ids_lines = self.input_data[ComponentType.line]["id"]
        self.n_power_sensors = self.n_lines * (
            1 if self.sensor_setting in ["from_pq", "to_pq"] else 2
        )
        self.n_current_sensors = self.n_lines * (
            1 if self.sensor_setting in ["from_i", "to_i"] else 2
        )
        if self.i_rated_general is not None:
            self.i_angle_sigma = i_sigma / i_rated_general * 2 * np.pi
        else:
            self.i_angle_sigma = None
        self.general_seed = general_seed

        self._validate_parameters()

    def _validate_parameters(self):
        """Validate that required parameters are provided based on sensor_setting."""
        # Validate that p_sigma and q_sigma are provided when sensor_setting is from_pq or to_pq
        if self.sensor_setting in ["from_pq", "to_pq"]:
            if self.p_sigma is None:
                raise ValueError(
                    f"p_sigma is required when sensor_setting is '{self.sensor_setting}'"
                )
            if self.q_sigma is None:
                raise ValueError(
                    f"q_sigma is required when sensor_setting is '{self.sensor_setting}'"
                )
        else:
            if self.i_sigma is None:
                raise ValueError(
                    f"i_sigma is required when sensor_setting is '{self.sensor_setting}'"
                )
            if self.i_rated_general is None:
                raise ValueError(
                    f"i_rated_general is required when sensor_setting is '{self.sensor_setting}'"
                )

    def _load_network(self):
        if self.network_name == "cigre_mv":
            self.input_data = json_deserialize_from_file(
                Path("cigre_mv_in_pgm.json"))
        else:
            self.input_data = json_deserialize_from_file(
                Path("cigre_lv_in_pgm.json"))

    def _change_switch_status(self):
        # change the to_status of the switches
        for i in range(len(self.switch_index)):
            self.input_data[ComponentType.line][self.switch_index[i]]["to_status"] = (
                self.switch_status[i]
            )

    def _get_voltage_sensor_index(self):
        self.voltage_sensor_index = get_component_indices(
            self.voltage_sensor_id,
            self.input_data,
            ComponentType.node
        )


    def run_pf(self) -> Dict:
        model = PowerGridModel(self.input_data)
        self.pf_output_data = model.calculate_power_flow(
            symmetric=True,
            error_tolerance=1e-8,
            max_iterations=20,
            calculation_method=CalculationMethod.newton_raphson,
        )
        self.x_pf = np.array(self.pf_output_data[ComponentType.node]["u"]) * np.exp(
            1j * np.array(self.pf_output_data[ComponentType.node]["u_angle"])
        )
        return self.pf_output_data

    def setup_se_input(self):
        # get the biggest component ID before creating sensors
        max_id = find_max_id(self.input_data)
        self.input_data_se = self.input_data.copy()
        self.sym_voltage_sensor, max_id = self._setup_voltage_sensor(max_id)
        if self.sensor_setting in ["from_pq", "to_pq"]:
            self.sym_power_sensor, max_id = self._setup_power_sensor(max_id)
            self.input_data_se[ComponentType.sym_power_sensor] = self.sym_power_sensor
            self.sym_current_sensor = None
        elif self.sensor_setting in ["from_i", "to_i"]:
            self.sym_current_sensor, max_id = self._setup_current_sensor(
                max_id)
            self.input_data_se[ComponentType.sym_current_sensor] = (
                self.sym_current_sensor
            )
            self.sym_power_sensor = None
        else:
            raise ValueError(
                f"sensor_setting must be 'from_pq', 'to_pq', 'from_i', or 'to_i', but got {self.sensor_setting}"
            )

        # Create the input data for the state estimation
        self.input_data_se[ComponentType.sym_voltage_sensor] = self.sym_voltage_sensor
        return (
            self.input_data_se,
            self.sym_voltage_sensor,
            self.sym_power_sensor,
            self.sym_current_sensor,
        )

    def _setup_voltage_sensor(self, max_id):
        np.random.seed(self.general_seed)
        output_data = self.pf_output_data
        voltage_sensor_id = self.voltage_sensor_id
        voltage_sensor_index = self.voltage_sensor_index
        u_sigma = self.u_sigma
        u_angle_sigma = self.u_angle_sigma
        sym_voltage_sensor = initialize_array(
            DatasetType.input, ComponentType.sym_voltage_sensor, len(
                voltage_sensor_id)
        )
        sym_voltage_sensor["id"] = [
            i for i in range(1, len(voltage_sensor_id) + 1)
        ] + max_id
        max_id += len(voltage_sensor_id)
        sym_voltage_sensor["measured_object"] = voltage_sensor_id
        sym_voltage_sensor["u_sigma"] = [u_sigma] * len(voltage_sensor_id)
        if self.network_name == "cigre_lv":
            # change the sigma for node 0, 1, 20,23 to 100
            # their index in the measured nodes are 0,1
            sym_voltage_sensor["u_sigma"][0] = 100
            sym_voltage_sensor["u_sigma"][1] = 100
            sym_voltage_sensor["u_sigma"][4] = 100
            sym_voltage_sensor["u_sigma"][7] = 100
        sym_voltage_sensor["u_measured"] = output_data[ComponentType.node]["u"][
            voltage_sensor_index
        ] + np.random.normal(0, sym_voltage_sensor["u_sigma"], len(voltage_sensor_id))
        sym_voltage_sensor["u_angle_measured"] = output_data[ComponentType.node][
            "u_angle"
        ][voltage_sensor_index] + np.random.normal(
            0, u_angle_sigma, len(voltage_sensor_id)
        )
        return sym_voltage_sensor, max_id

    def _setup_power_sensor(self, max_id):
        output_data = self.pf_output_data
        p_sigma = self.p_sigma
        q_sigma = self.q_sigma
        n_power_sensors = self.n_power_sensors
        n_lines = self.n_lines
        ids_lines = self.ids_lines
        sym_power_sensor = initialize_array(
            DatasetType.input, ComponentType.sym_power_sensor, n_power_sensors
        )
        sym_power_sensor["id"] = [
            i + 1 for i in range(n_power_sensors)] + max_id
        max_id += n_power_sensors
        sym_power_sensor["measured_object"] = np.tile(ids_lines, 1)
        sym_power_sensor["p_sigma"] = [p_sigma] * n_power_sensors
        sym_power_sensor["q_sigma"] = [q_sigma] * n_power_sensors
        if self.sensor_setting == "from_pq":
            measured_terminal_type = MeasuredTerminalType.branch_from
            p_side = "p_from"
            q_side = "q_from"
            # Get the from_node for each line
            node_ids_with_power_sensors = self.input_data[ComponentType.line]["from_node"]
        elif self.sensor_setting == "to_pq":
            measured_terminal_type = MeasuredTerminalType.branch_to
            p_side = "p_to"
            q_side = "q_to"
            node_ids_with_power_sensors = self.input_data[ComponentType.line]["to_node"]
        else:
            raise ValueError(
                f"sensor_setting must be 'from_pq' or 'to_pq', but got {self.sensor_setting}"
            )
        sym_power_sensor["measured_terminal_type"] = [
            measured_terminal_type] * n_lines
        sym_power_sensor["p_measured"] = np.concatenate(
            [output_data[ComponentType.line][p_side]]
        ) + np.random.normal(0, sym_power_sensor["p_sigma"], n_power_sensors)
        sym_power_sensor["q_measured"] = np.concatenate(
            [output_data[ComponentType.line][q_side]]
        ) + np.random.normal(0, sym_power_sensor["q_sigma"], n_power_sensors)
        # get corresponding u_rated for the power sensors
        u_rated_at_power_sensors = self.input_data[ComponentType.node]["u_rated"][node_ids_with_power_sensors]
        self.u_rated_at_power_sensors = u_rated_at_power_sensors
        self.node_ids_with_power_sensors = node_ids_with_power_sensors

        return sym_power_sensor, max_id

    def _setup_current_sensor(self, max_id):
        np.random.seed(self.general_seed)
        output_data = self.pf_output_data
        x_pf = self.x_pf
        self._h_matrix_gen()
        if self.sensor_setting == "from_i":
            i_pf = self.H_line_current_from @ x_pf
            measured_terminal_type = MeasuredTerminalType.branch_from
            i_side = "i_from"
            reference_sign = 1
        elif self.sensor_setting == "to_i":
            i_pf = self.H_line_current_to @ x_pf
            measured_terminal_type = MeasuredTerminalType.branch_to
            i_side = "i_to"
            # It seems that the reference direction of the current sensor at to_side
            # is different from the reference direction of the current in PGM PF.
            reference_sign = -1
        else:
            raise ValueError(
                f"sensor_setting must be 'from_i' or 'to_i', but got {self.sensor_setting}"
            )
        i_pf_angle = np.angle(i_pf)
        n_lines = self.n_lines
        n_current_sensors = self.n_current_sensors
        i_sigma = self.i_sigma
        i_angle_sigma = self.i_angle_sigma
        ids_lines = self.ids_lines
        sym_current_sensor = initialize_array(
            DatasetType.input, ComponentType.sym_current_sensor, n_current_sensors
        )
        sym_current_sensor["id"] = [
            i + 1 for i in range(n_current_sensors)] + max_id
        max_id += n_current_sensors
        sym_current_sensor["measured_object"] = np.tile(ids_lines, 1)
        sym_current_sensor["i_sigma"] = [i_sigma] * n_current_sensors
        sym_current_sensor["i_angle_sigma"] = [
            i_angle_sigma] * n_current_sensors
        sym_current_sensor["measured_terminal_type"] = [
            measured_terminal_type
        ] * n_lines
        sym_current_sensor["angle_measurement_type"] = [
            AngleMeasurementType.global_angle
        ] * n_lines
        sym_current_sensor["i_measured"] = reference_sign * np.concatenate(
            [output_data[ComponentType.line][i_side]]
        ) + np.random.normal(0, sym_current_sensor["i_sigma"], n_current_sensors)
        sym_current_sensor["i_angle_measured"] = i_pf_angle + np.random.normal(
            0, sym_current_sensor["i_angle_sigma"], n_current_sensors
        )
        return sym_current_sensor, max_id

    def _h_matrix_gen(self):
        h_matrix_gen = HMatrixGenerator(input_data=self.input_data)
        (
            self.H_voltage,
            self.H_line_current_from,
            self.H_line_current_to,
            self.H_transformer_current_from,
            self.H_transformer_current_to,
        ) = h_matrix_gen.generate_h_matrix(whole_return=False)
