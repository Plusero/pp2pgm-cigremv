import pandapower as pp
import pandapower.networks as pn
from power_grid_model_io.converters import PandaPowerConverter


class PandaPowerNetwork2PGM:
    def __init__(self, net_name="ieee14"):
        if net_name == "ieee14":
            # Load the IEEE 14-bus network from pandapower
            self.net = pn.case14()
            self.replace_pv_nodes_with_pq_nodes()
        elif net_name == "cigre_mv":
            # Load the CIGRE MV network from pandapower
            self.net = pn.create_cigre_network_mv(with_der=False)
        elif net_name == "cigre_lv":
            # Load the CIGRE LV network from pandapower
            self.net = pn.create_cigre_network_lv()
        elif net_name == "mv_oberhein":
            # Load the MV Oberhein network from pandapower
            self.net = pn.mv_oberrhein("generation")
        else:
            raise ValueError(f"Network {net_name} not supported.")

        converter = PandaPowerConverter()
        self.input_data, self.extra_info = converter.load_input_data(self.net)

    def to_pgm(self):
        # Convert pandapower network to PGM format
        converter = PandaPowerConverter()
        pgm_net = converter.convert(self.net)
        return pgm_net

    def replace_pv_nodes_with_pq_nodes(self):
        # Convert PV generators to PQ loads
        # Get the current P and Q values from the generators
        gen_buses = self.net.gen.bus.values
        gen_p_mw = self.net.gen.p_mw.values

        print(f"\nGenerators at buses: {gen_buses}")
        print(f"Generator P values: {gen_p_mw}")
        print(f'Original voltage setpoints: {self.net.gen.vm_pu.values}')
        print(
            f"Rated voltages of generator buses: {self.net.bus.vn_kv.values[gen_buses]}")

        # Run a power flow first to get the actual Q values
        pp.runpp(self.net)
        gen_q_mvar = self.net.res_gen.q_mvar.values

        print(f"Generator Q values from power flow: {gen_q_mvar}")

        # replace the PV generators with PQ generators
        for i, bus in enumerate(gen_buses):
            # Add a static load at the same bus
            pp.create_load(
                self.net, bus=bus, p_mw=gen_p_mw[i], q_mvar=gen_q_mvar[i], name=f"static_gen_{bus}")
        print(f"type of self.net.gen: {type(self.net.gen)}")
        # Remove the original generators
        self.net.gen.drop(self.net.gen.index, inplace=True)

        # Change bus types from PV to PQ
        for bus in gen_buses:
            self.net.bus.loc[self.net.bus.index[self.net.bus.index == bus],
                             'type'] = 'b'  # 'b' means PQ bus
