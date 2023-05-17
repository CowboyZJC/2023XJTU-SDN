from ryu.base import app_manager 
from ryu.controller import ofp_event 
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER 
from ryu.controller.handler import set_ev_cls 
from ryu.ofproto import ofproto_v1_3 
from ryu.lib.packet import packet 
from ryu.lib.packet import ethernet 
class Switch(app_manager.RyuApp): 
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION] 
    def __init__(self, *args, **kwargs): #可以接受任意个参数
        super(Switch, self).__init__(*args, **kwargs)
        # maybe you need a global data structure to save the mapping
        #初始化交换机
        self.mac_to_port = {}#初始化空
        
    def add_flow(self, datapath, priority, match, actions,idle_timeout=0,hard_timeout=0):#下发流表
        dp = datapath 
        ofp = dp.ofproto 
        parser = dp.ofproto_parser 
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)] 
        mod = parser.OFPFlowMod(datapath=dp, priority=priority, 
                                idle_timeout=idle_timeout,
                                hard_timeout=hard_timeout,
        						match=match,instructions=inst) 
        dp.send_msg(mod) 
        
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER) 
    def switch_features_handler(self, ev): 
        msg = ev.msg 
        dp = msg.datapath 0
        ofp = dp.ofproto 
        parser = dp.ofproto_parser
        match = parser.OFPMatch() 
        actions = [parser.OFPActionOutput(ofp.OFPP_CONTROLLER,ofp.OFPCML_NO_BUFFER)] 
        self.add_flow(dp, 0, match, actions)
        
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER) 
    def packet_in_handler(self, ev): 
        msg = ev.msg 
        dp = msg.datapath 
        ofp = dp.ofproto 
        parser = dp.ofproto_parser 
        
        # the identity of switch 
        dpid = dp.id 
        self.mac_to_port.setdefault(dpid,{}) 
        # the port that receive the packet 
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data) 
        eth_pkt = pkt.get_protocol(ethernet.ethernet) 
        # get the mac 
        dst = eth_pkt.dst 
        src = eth_pkt.src 
        # we can use the logger to print some useful information 
        self.logger.info('packet: %s %s %s %s', dpid, src, dst, in_port)

        
        # you need to code here to avoid the direct flooding 
        # having fun 
        # :)
        # 学习mac地址
        self.mac_to_port[dpid][src] = in_port#mac 到 端口的对应

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]#匹配到目的mac 则把转发端口号赋值给 outport
        else:
            out_port = ofproto.OFPP_FLOOD#未匹配到则洪泛

        actions = [parser.OFPActionOutput(out_port)] #数据包转发

        # install a flow to avoid packet_in next time下发流表

        #没有洪泛则需要下发流表
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            # verify if we have a valid buffer_id, if yes avoid to send both
            # flow_mod & packet_out
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)


        
