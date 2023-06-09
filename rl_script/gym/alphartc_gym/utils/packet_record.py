#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from turtle import delay
import numpy as np


class PacketRecord:
    # feature_interval can be modified
    def __init__(self, base_delay_ms=200):
        self.base_delay_ms = base_delay_ms
        self.reset()

    def reset(self):
        self.packet_num = 0
        self.packet_list = []  # ms
        self.last_seqNo = {}
        # self.timer_delta = None  # ms
        self.min_seen_delay = self.base_delay_ms  # ms
        # ms, record the rtime of the last packet in last interval,
        self.last_interval_rtime = None

    def clear(self):
        self.packet_num = 0
        if self.packet_list:
            self.last_interval_rtime = self.packet_list[-1]['timestamp']
        self.packet_list = []

    def on_receive(self, packet_info):
        # print("on receive!")
        assert (len(self.packet_list) == 0
                or packet_info.receive_timestamp
                >= self.packet_list[-1]['timestamp']), \
            "The incoming packets receive_timestamp disordered"

        # Calculate the loss count
        loss_count = 0
        # print("self.last_seqNo:"+str(self.last_seqNo))
        
        if packet_info.ssrc in self.last_seqNo:
            # print("packet_info.sequence_number:"+str(packet_info.sequence_number)+" self.last_seqNo[packet_info.ssrc]"+str(self.last_seqNo[packet_info.ssrc]))
            loss_count = max(0,
                packet_info.sequence_number - self.last_seqNo[packet_info.ssrc] - 1)
            # print("loss_count:"+str(loss_count))
        self.last_seqNo[packet_info.ssrc] = packet_info.sequence_number
        # print(self.last_seqNo[packet_info.ssrc])
        # Calculate packet delay
        # if self.timer_delta is None:
        #     # shift delay of the first packet to base delay
        #     self.timer_delta = self.base_delay_ms - \
        #         (packet_info.receive_timestamp - packet_info.send_timestamp)    
            # print("matthew:Time delta:"+str(self.timer_delta)+" receive_time:"+str(packet_info.receive_timestamp)+" send_time:"+str(packet_info.send_timestamp))
        
        delay = (packet_info.receive_timestamp - packet_info.send_timestamp)
        # print("matthew:delay:"+str(delay))
        # print("matthew:packet_info.receive_timestamp:"+str(packet_info.receive_timestamp)+" packet_info.send_timestamp"+str(packet_info.send_timestamp))
        self.min_seen_delay = min(delay, self.min_seen_delay)
        
        # Check the last interval rtime
        if self.last_interval_rtime is None:
            self.last_interval_rtime = packet_info.receive_timestamp

        # Record result in current packet
        packet_result = {
            'timestamp': packet_info.receive_timestamp,  # ms
            'delay': delay,  # ms
            'payload_byte': packet_info.payload_size,  # B
            'loss_count': loss_count,  # p
            'bandwidth_prediction': packet_info.bandwidth_prediction  # bps
        }
        self.packet_list.append(packet_result)
        self.packet_num += 1

    def _get_result_list(self, interval, key):
        if self.packet_num == 0:
            return []

        result_list = []
        if interval == 0:
            interval = self.packet_list[-1]['timestamp'] -\
                self.last_interval_rtime
            # print("self.packet_list[-1]['timestamp']:"+str(self.packet_list[-1]['timestamp'])+" self.last_interval_rtime:"+str(self.last_interval_rtime))
        
        start_time = self.packet_list[-1]['timestamp'] - interval
        # print("start time:"+str(start_time))
        index = self.packet_num - 1
        while index >= 0 and self.packet_list[index]['timestamp'] > start_time:
            # print("matthew:packet"+str(index)+" :"+str(self.packet_list[index][key]))
            result_list.append(self.packet_list[index][key])
            index -= 1
        return result_list

    def calculate_average_delay(self, interval=0):
        '''
        Calulate the average delay in the last interval time,
        interval=0 means based on the whole packets
        The unit of return value: ms
        '''
        delay_list = self._get_result_list(interval=interval, key='delay')
        if delay_list:
            return np.mean(delay_list)
        else:
            return 0

    def calculate_loss_ratio(self, interval=0):
        '''
        Calulate the loss ratio in the last interval time,
        interval=0 means based on the whole packets
        The unit of return value: packet/packet
        '''
        loss_list = self._get_result_list(interval=interval, key='loss_count')
        # print("loss list:"+str(loss_list))
        if loss_list:
            loss_num = np.sum(loss_list)
            received_num = len(loss_list)
            # print("loss_num:"+str(loss_num)+" received_num:"+str(received_num))
            return loss_num / (loss_num + received_num)
        else:
            return 0

    def calculate_receiving_rate(self, interval=0):
        '''
        Calulate the receiving rate in the last interval time,
        interval=0 means based on the whole packets
        The unit of return value: bps
        '''
        received_size_list = self._get_result_list(interval=interval, key='payload_byte')
        if received_size_list:
            received_nbytes = np.sum(received_size_list)
            if interval == 0:
                interval = self.packet_list[-1]['timestamp'] -\
                    self.last_interval_rtime
            return received_nbytes * 8 / interval * 1000
        else:
            return 0

    def calculate_latest_prediction(self):
        '''
        The unit of return value: bps
        '''
        if self.packet_num > 0:
            return self.packet_list[-1]['bandwidth_prediction']
        else:
            return 0