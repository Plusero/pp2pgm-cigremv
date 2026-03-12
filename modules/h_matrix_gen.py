import numpy as np
from power_grid_model import ComponentType
# TODO: add checks for transformer current measurements, if there is no, then do not add H_transformer_current to H.


class HMatrixGenerator:
    """
    Class to generate the H matrix for state estimation based on the input data of PGM (Power Grid Model).

    Attributes:
        input_data (dict): The input data of PGM containing information about nodes, lines, and transformers.
        n_nodes (int): Number of nodes in the power grid.
        n_lines (int): Number of lines in the power grid.
        n_transformers (int): Number of transformers in the power grid.
        num_states (int): Total number of states in the power grid.
        num_measurements (int): Total number of measurements in the power grid.
    """

    def __init__(self, input_data: dict):
        """
        Initialize the HMatrixGenerator with the input data.

        Args:
            input_data (dict): The input data of PGM containing information about nodes, lines, and transformers.
        """
        self.input_data = input_data
        # number of components
        self.n_nodes = len(self.input_data[ComponentType.node]["id"])
        self.n_lines = len(self.input_data[ComponentType.line]["id"])
        self.n_transformers = (
            len(self.input_data[ComponentType.transformer]["id"])
            if ComponentType.transformer in self.input_data
            else 0
        )
        self.num_states = len(self.input_data[ComponentType.node]["id"])
        self.num_measurements = (
            self.n_nodes + self.n_lines * 2 + self.n_transformers * 2
        )
        self.input_data = input_data
        self.H = np.zeros(
            (self.num_measurements, self.num_states), dtype=complex)
        # H matrix for voltage measurements
        self.H_voltage = np.zeros(
            (self.num_measurements, self.num_states), dtype=complex
        )
        # H matrix for transformer current measurements
        self.H_line_current_from = np.zeros(
            (self.n_lines, self.n_nodes), dtype=complex)
        self.H_line_current_to = np.zeros(
            (self.n_lines, self.n_nodes), dtype=complex)
        # H matrix for transformer current measurements
        self.H_transformer_current_from = np.zeros(
            (self.n_transformers, self.n_nodes), dtype=complex
        )
        self.H_transformer_current_to = np.zeros(
            (self.n_transformers, self.n_nodes), dtype=complex
        )
        self.id_to_index = {
            node: index for index, node in enumerate(self.input_data[ComponentType.node]["id"])}

    def generate_h_matrix(self, whole_return: bool = True):
        """
        Generate the H matrix for state estimation based on the input data of PGM.

        Args:
            whole_return (bool): Whether to return the whole H matrix or the parts of H matrix.

        Returns:
            H (np.ndarray): The H matrix for state estimation.
            The H matrix is a m by n matrix, where m is the number of measurements and n is the number of states.
            It consists of three parts:
                - H_voltage: The H matrix for voltage measurements.
                - H_line_current: The H matrix for line current measurements.
                - H_transformer_current: The H matrix for transformer current measurements.
            These three parts are concatenated along the first dimension.
        """

        self.generate_h_matrix_voltage()
        self.generate_h_matrix_line_current()
        if self.n_transformers > 0:
            self.generate_h_matrix_transformer_current()
        else:
            self.H_transformer_current = None
        matrices_to_concat = [
            matrix for matrix in [self.H_voltage, self.H_line_current, self.H_transformer_current]
            if matrix is not None
        ]

        self.H = np.concatenate(matrices_to_concat, axis=0)
        if whole_return:
            return self.H
        else:
            return (
                self.H_voltage,
                self.H_line_current_from,
                self.H_line_current_to,
                self.H_transformer_current_from,
                self.H_transformer_current_to,
            )

    def generate_h_matrix_voltage(self):
        """
        Generate the H matrix for voltage measurements from the input_data of PGM.

        Returns:
            H_voltage (np.ndarray): The H matrix for voltage measurements. A diagonal matrix with ones.
        """
        self.H_voltage = np.diag(np.ones(self.n_nodes))
        return self.H_voltage

    def generate_h_matrix_line_current(self):
        """
        Generate the H matrix for line current measurements from the input_data of PGM.

        Returns:
            H_line_current (np.ndarray): The H matrix for line current measurements.
            H_line_current is a n_lines*2 by n_nodes matrix.
            The first n_lines rows are for I_from, the last n_lines rows are for I_to.
        """
        # loop over each line
        for i in range(self.n_lines):
            # get the from and to nodes of the line
            from_node = self.input_data[ComponentType.line]["from_node"][i]
            from_node_index = self.id_to_index[from_node]
            to_node = self.input_data[ComponentType.line]["to_node"][i]
            to_node_index = self.id_to_index[to_node]
            r = self.input_data[ComponentType.line]["r1"][i]
            x = self.input_data[ComponentType.line]["x1"][i]
            c = self.input_data[ComponentType.line]["c1"][i]
            Y_tmp = 1 / (r + x * 1j)
            Y_s_tmp = 1j * 2 * np.pi * 50 * c
            from_status = self.input_data[ComponentType.line]["from_status"][i]
            to_status = self.input_data[ComponentType.line]["to_status"][i]
            # put the Y and Ys to the corresponding location of H_current
            # handling the switch status with different cases
            if from_status == 1 and to_status == 1:
                self.H_line_current_from[i, from_node_index] = (
                    Y_tmp + Y_s_tmp / 2
                ) / np.sqrt(3)
                self.H_line_current_from[i,
                                         to_node_index] = (-Y_tmp) / np.sqrt(3)
                self.H_line_current_to[i, from_node_index] = (
                    Y_tmp) / np.sqrt(3)
                self.H_line_current_to[i,
                                       to_node_index] = (-Y_tmp - Y_s_tmp / 2) / np.sqrt(3)
            elif from_status == 1 and to_status == 0:
                # all the shunt admittance is for the from side, so not divided by 2
                self.H_line_current_from[i,
                                         from_node_index] = Y_s_tmp / np.sqrt(3)
                self.H_line_current_from[i, to_node_index] = 0 + 0j
                self.H_line_current_to[i, from_node_index] = 0 + 0j
                self.H_line_current_to[i, to_node_index] = 0 + 0j
            elif from_status == 0 and to_status == 1:
                self.H_line_current_from[i, from_node_index] = 0 + 0j
                self.H_line_current_from[i, to_node_index] = 0 + 0j
                self.H_line_current_to[i, from_node_index] = 0 + 0j
                # all the shunt admittance is for the to side, so not divided by 2
                self.H_line_current_to[i, to_node_index] = Y_s_tmp / np.sqrt(3)
            else:
                self.H_line_current_from[i, from_node_index] = 0
                self.H_line_current_from[i, to_node_index] = 0
                self.H_line_current_to[i, from_node_index] = 0
                self.H_line_current_to[i, to_node_index] = 0
            self.H_line_current = np.concatenate(
                (self.H_line_current_from, self.H_line_current_to), axis=0
            )
        return self.H_line_current

    def generate_h_matrix_transformer_current(self) -> np.ndarray:
        """
        Generate the H matrix for transformer current measurements from the input_data of PGM.

        Returns:
            H_transformer_current (np.ndarray): The H matrix for transformer current measurements.
            H_transformer_current is a n_transformers*2 by n_nodes matrix.
            The first n_transformers rows are for I_from, the last n_transformers rows are for I_to.
        """
        # loop over each transformer
        for i in range(self.n_transformers):
            # get parameters of the transformer
            from_node = self.input_data[ComponentType.transformer]["from_node"][i]
            from_node_index = self.id_to_index[from_node]
            to_node = self.input_data[ComponentType.transformer]["to_node"][i]
            to_node_index = self.id_to_index[to_node]
            uk = self.input_data[ComponentType.transformer]["uk"][i]
            u1 = self.input_data[ComponentType.transformer]["u1"][i]
            u2 = self.input_data[ComponentType.transformer]["u2"][i]
            n = u1 / u2  # turns ratio
            pk = self.input_data[ComponentType.transformer]["pk"][i]
            sn = self.input_data[ComponentType.transformer]["sn"][i]
            i0 = self.input_data[ComponentType.transformer]["i0"][i]
            p0 = self.input_data[ComponentType.transformer]["p0"][i]
            clock = self.input_data[ComponentType.transformer]["clock"][i]
            phase_shift = clock / 12 * 2 * np.pi
            # According to me
            s_base = sn
            z_base = u2 * u2 / s_base  # V*V/(V*A) = Ohm
            y_base = 1 / z_base  # 1/Ohm = S
            z_series_abs = uk * z_base  # 1*Ohm = Ohm
            z_series_real = pk / sn * z_base  # W/W*Ohm = Ohm
            z_series_imag_squared = z_series_abs**2 - z_series_real**2
            uk_sign = np.sign(uk)
            z_series_imag = (
                uk_sign * np.sqrt(z_series_imag_squared)
                if z_series_imag_squared > 0.0
                else 0.0
            )
            z_series = z_series_real + 1j * z_series_imag  #
            y_series = 1 / z_series  # 1/Ohm = S
            y_shunt_abs = i0 * y_base  # 1*S = S
            y_shunt_real = p0 / sn * y_base  # W/W*S= S
            y_shunt_imag = -np.sqrt(y_shunt_abs**2 - y_shunt_real**2)
            y_shunt = y_shunt_real + 1j * y_shunt_imag
            self.H_transformer_current_from[i, from_node_index] = (
                (y_series + y_shunt / 2) / np.sqrt(3) / n / n
            )
            self.H_transformer_current_from[i, to_node_index] = (
                -y_series / np.sqrt(3) / n * np.exp(1j * phase_shift)
            )
            self.H_transformer_current_to[i, from_node_index] = (
                y_series / np.sqrt(3) / n * np.exp(-1j * phase_shift)
            )
            self.H_transformer_current_to[i, to_node_index] = (
                -y_series - y_shunt / 2
            ) / np.sqrt(3)
        self.H_transformer_current = np.concatenate(
            (self.H_transformer_current_from, self.H_transformer_current_to), axis=0
        )
        return self.H_transformer_current
