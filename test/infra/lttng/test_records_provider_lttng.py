# Copyright 2021 Research Institute of Systems Planning, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import List

from caret_analyze.exceptions import UnsupportedNodeRecordsError
from caret_analyze.infra.infra_helper import InfraHelper
from caret_analyze.infra.lttng import Lttng
from caret_analyze.infra.lttng.bridge import LttngBridge
from caret_analyze.infra.lttng.column_names import COLUMN_NAME
from caret_analyze.infra.lttng.records_provider_lttng import (NodeRecordsCallbackChain,
                                                              NodeRecordsInheritUniqueTimestamp,
                                                              RecordsProviderLttng,
                                                              RecordsProviderLttngHelper)
from caret_analyze.infra.lttng.value_objects import (PublisherValueLttng,
                                                     SubscriptionCallbackValueLttng,
                                                     TimerCallbackValueLttng)
from caret_analyze.record import Record, Records, RecordsInterface
from caret_analyze.record.interface import RecordInterface
from caret_analyze.value_objects import (CallbackChain, CallbackStructValue,
                                         CommunicationStructValue,
                                         NodePathStructValue,
                                         PublisherStructValue,
                                         SubscriptionCallbackStructValue,
                                         TimerCallbackStructValue,
                                         VariablePassingStructValue)

from pytest_mock import MockerFixture


class TestRecordsProviderLttng:

    def test_timer_callback_records(self, mocker: MockerFixture):
        period_ns = 10

        lttng_mock = mocker.Mock(spec=Lttng)
        callback_info = TimerCallbackStructValue(
            'node', 'symbol', period_ns, None, 'callback_0')
        callback_object = 5
        callback_info_lttng = TimerCallbackValueLttng(
            'callback_id', 'node_id', callback_info.node_name,
            callback_info.symbol, callback_info.period_ns,
            callback_info.publish_topic_names, callback_object)

        records_mock = mocker.Mock(spec=RecordsInterface)
        mocker.patch.object(records_mock, 'data', [])
        helper_mock = mocker.Mock(spec=RecordsProviderLttngHelper)
        mocker.patch(
            'caret_analyze.infra.lttng.records_provider_lttng.RecordsProviderLttngHelper',
            return_value=helper_mock)
        mocker.patch.object(helper_mock, 'get_callback_objects',
                            return_value=[callback_object])

        def filter_if(condition):
            record_mock = mocker.Mock(spec=RecordInterface)
            mocker.patch.object(record_mock, 'get',
                                return_value=callback_object+1)
            assert condition(record_mock) is False
            mocker.patch.object(record_mock, 'get',
                                return_value=callback_object)
            assert condition(record_mock) is True
            return records_mock

        mocker.patch.object(records_mock, 'filter_if', side_effect=filter_if)
        mocker.patch.object(records_mock, 'clone', return_value=records_mock)
        mocker.patch.object(lttng_mock, 'get_timer_callbacks', return_value=[
                            callback_info_lttng])
        mocker.patch.object(
            lttng_mock, 'compose_callback_records', return_value=records_mock)

        provider = RecordsProviderLttng(lttng_mock)

        records = provider.callback_records(callback_info)
        assert len(records.data) == 0

    def test_subscription_callback_records_with_intra(self, mocker: MockerFixture):
        topic_name = 'topic'
        node_name = '/node'
        symbol = 'symbol'
        cb_name = 'callback_0'

        lttng_mock = mocker.Mock(spec=Lttng)
        callback_info = SubscriptionCallbackStructValue(
            node_name, symbol, topic_name, None, cb_name)
        callback_object = 5
        callback_object_intra = 6

        records: RecordsInterface
        records = Records(
            [
                Record({
                    COLUMN_NAME.CALLBACK_OBJECT: callback_object,
                    COLUMN_NAME.CALLBACK_START_TIMESTAMP: 1,
                    COLUMN_NAME.CALLBACK_END_TIMESTAMP: 2,
                }),
                Record({
                    COLUMN_NAME.CALLBACK_OBJECT: callback_object_intra,
                    COLUMN_NAME.CALLBACK_START_TIMESTAMP: 0,
                    COLUMN_NAME.CALLBACK_END_TIMESTAMP: 1,
                }),
                Record({
                    COLUMN_NAME.CALLBACK_OBJECT: callback_object + 999,
                    COLUMN_NAME.CALLBACK_START_TIMESTAMP: 2,
                    COLUMN_NAME.CALLBACK_END_TIMESTAMP: 3,
                })
            ],
            [COLUMN_NAME.CALLBACK_OBJECT,
             COLUMN_NAME.CALLBACK_START_TIMESTAMP,
             COLUMN_NAME.CALLBACK_END_TIMESTAMP]
        )

        helper_mock = mocker.Mock(spec=RecordsProviderLttngHelper)
        mocker.patch(
            'caret_analyze.infra.lttng.records_provider_lttng.RecordsProviderLttngHelper',
            return_value=helper_mock)
        mocker.patch.object(helper_mock, 'get_callback_objects',
                            return_value=[callback_object, callback_object_intra])

        callback_info_lttng = SubscriptionCallbackValueLttng(
            'callback_id', 'node_id', callback_info.node_name, symbol,
            topic_name, callback_info.publish_topic_names,
            callback_object, callback_object_intra)
        mocker.patch.object(lttng_mock, 'get_subscription_callbacks', return_value=[
                            callback_info_lttng])
        mocker.patch.object(
            lttng_mock, 'compose_callback_records', return_value=records)

        provider = RecordsProviderLttng(lttng_mock)

        records = provider.callback_records(callback_info)
        assert len(records.data) == 2

    def test_subscription_callback_records_without_intra(self, mocker: MockerFixture):
        topic_name = 'topic'
        node_name = '/node'
        symbol = 'symbol'
        cb_name = 'callback_0'
        pub_topic_names = None

        lttng_mock = mocker.Mock(spec=Lttng)
        callback_info = SubscriptionCallbackStructValue(
            node_name, symbol, topic_name, pub_topic_names, cb_name)
        callback_object = 5
        callback_object_intra = None

        records: RecordsInterface
        records = Records(
            [
                Record({
                    COLUMN_NAME.CALLBACK_OBJECT: callback_object,
                    COLUMN_NAME.CALLBACK_START_TIMESTAMP: 2,
                    COLUMN_NAME.CALLBACK_END_TIMESTAMP: 3,
                }),
                Record({
                    COLUMN_NAME.CALLBACK_OBJECT: callback_object_intra,
                    COLUMN_NAME.CALLBACK_START_TIMESTAMP: 2,
                    COLUMN_NAME.CALLBACK_END_TIMESTAMP: 3,
                }),
                Record({
                    COLUMN_NAME.CALLBACK_OBJECT: callback_object + 999,
                    COLUMN_NAME.CALLBACK_START_TIMESTAMP: 2,
                    COLUMN_NAME.CALLBACK_END_TIMESTAMP: 3,
                })
            ],
            [COLUMN_NAME.CALLBACK_OBJECT,
             COLUMN_NAME.CALLBACK_START_TIMESTAMP,
             COLUMN_NAME.CALLBACK_END_TIMESTAMP]
        )
        helper_mock = mocker.Mock(spec=RecordsProviderLttngHelper)
        mocker.patch(
            'caret_analyze.infra.lttng.records_provider_lttng.RecordsProviderLttngHelper',
            return_value=helper_mock)
        mocker.patch.object(helper_mock, 'get_callback_objects',
                            return_value=[callback_object])

        callback_info_lttng = SubscriptionCallbackValueLttng(
            'callback_id', 'node_id', node_name, symbol, topic_name, pub_topic_names,
            callback_object, callback_object_intra)
        mocker.patch.object(lttng_mock, 'get_subscription_callbacks', return_value=[
                            callback_info_lttng])
        mocker.patch.object(
            lttng_mock, 'compose_callback_records', return_value=records)

        provider = RecordsProviderLttng(lttng_mock)

        records = provider.callback_records(callback_info)
        assert len(records.data) == 1

    def test_node_records_callback_chain(self, mocker: MockerFixture):
        lttng_mock = mocker.Mock(spec=Lttng)
        node_path_info_mock = mocker.Mock(spec=NodePathStructValue)
        records_mock = mocker.Mock(spec=RecordsInterface)

        node_records_cb_chain_mock = mocker.Mock(spec=NodeRecordsCallbackChain)
        mocker.patch('caret_analyze.infra.lttng.records_provider_lttng.NodeRecordsCallbackChain',
                     return_value=node_records_cb_chain_mock)

        mocker.patch.object(node_records_cb_chain_mock,
                            'to_records', return_value=records_mock)
        provider = RecordsProviderLttng(lttng_mock)

        records = provider.node_records(node_path_info_mock)
        assert records == records_mock

    def test_inter_proc_comm_records(self, mocker: MockerFixture):
        lttng_mock = mocker.Mock(spec=Lttng)

        comm_mock = mocker.Mock(spec=CommunicationStructValue)
        pub_mock = mocker.Mock(spec=PublisherStructValue)
        sub_cb_mock = mocker.Mock(spec=SubscriptionCallbackStructValue)

        cb_object = 5
        pub_handle = 6

        records: RecordsInterface

        records = Records(
            [
                Record({
                    COLUMN_NAME.RCLCPP_INTER_PUBLISH_TIMESTAMP: 1,
                    COLUMN_NAME.DDS_WRITE_TIMESTAMP: 2,
                    COLUMN_NAME.RCL_PUBLISH_TIMESTAMP: 3,
                    COLUMN_NAME.CALLBACK_START_TIMESTAMP: 4,
                    COLUMN_NAME.PUBLISHER_HANDLE: pub_handle,
                    COLUMN_NAME.CALLBACK_OBJECT: cb_object,
                }),
                Record({
                    COLUMN_NAME.RCLCPP_INTER_PUBLISH_TIMESTAMP: 2,
                    COLUMN_NAME.DDS_WRITE_TIMESTAMP: 3,
                    COLUMN_NAME.RCL_PUBLISH_TIMESTAMP: 4,
                    COLUMN_NAME.CALLBACK_START_TIMESTAMP: 5,
                    COLUMN_NAME.PUBLISHER_HANDLE: pub_handle + 999,
                    COLUMN_NAME.CALLBACK_OBJECT: cb_object
                }),
                Record({
                    COLUMN_NAME.RCLCPP_INTER_PUBLISH_TIMESTAMP: 3,
                    COLUMN_NAME.DDS_WRITE_TIMESTAMP: 4,
                    COLUMN_NAME.RCL_PUBLISH_TIMESTAMP: 5,
                    COLUMN_NAME.CALLBACK_START_TIMESTAMP: 6,
                    COLUMN_NAME.PUBLISHER_HANDLE: pub_handle,
                    COLUMN_NAME.CALLBACK_OBJECT: cb_object + 999
                })
            ],
            [
                COLUMN_NAME.PUBLISHER_HANDLE,
                COLUMN_NAME.CALLBACK_OBJECT,
                COLUMN_NAME.RCLCPP_INTER_PUBLISH_TIMESTAMP,
                COLUMN_NAME.DDS_WRITE_TIMESTAMP,
                COLUMN_NAME.RCL_PUBLISH_TIMESTAMP,
                COLUMN_NAME.CALLBACK_START_TIMESTAMP,
            ]
        )

        mocker.patch.object(comm_mock, 'publisher', pub_mock)
        mocker.patch.object(comm_mock, 'subscribe_callback', sub_cb_mock)

        helper_mock = mocker.Mock(spec=RecordsProviderLttngHelper)
        mocker.patch(
            'caret_analyze.infra.lttng.records_provider_lttng.RecordsProviderLttngHelper',
            return_value=helper_mock)
        mocker.patch.object(helper_mock, 'get_subscription_callback_object_inter',
                            return_value=cb_object)
        mocker.patch.object(helper_mock, 'get_publisher_handles',
                            return_value=[pub_handle])

        mocker.patch.object(
            lttng_mock, 'compose_inter_proc_comm_records', return_value=records)
        provider = RecordsProviderLttng(lttng_mock)

        records = provider._compose_inter_proc_comm_records(comm_mock)
        assert len(records.data) == 1

    def test_node_records_inherit_timestamp(self, mocker: MockerFixture):
        lttng_mock = mocker.Mock(spec=Lttng)
        node_path_info_mock = mocker.Mock(spec=NodePathStructValue)
        records_mock = mocker.Mock(spec=RecordsInterface)

        mocker.patch('caret_analyze.infra.lttng.records_provider_lttng.NodeRecordsCallbackChain',
                     side_effect=UnsupportedNodeRecordsError(''))

        node_records_inherit_timestamp_mock = mocker.Mock(
            spec=NodeRecordsInheritUniqueTimestamp)
        mocker.patch(
            'caret_analyze.infra.lttng.records_provider_lttng.NodeRecordsInheritUniqueTimestamp',
            return_value=node_records_inherit_timestamp_mock)

        mocker.patch.object(node_records_inherit_timestamp_mock,
                            'to_records', return_value=records_mock)
        provider = RecordsProviderLttng(lttng_mock)

        records = provider.node_records(node_path_info_mock)
        assert records == records_mock

    def test_get_publish_records(self, mocker: MockerFixture):
        lttng_mock = mocker.Mock(spec=Lttng)

        pub_mock = mocker.Mock(spec=PublisherStructValue)

        cb_object = 5
        pub_handle = 6

        records: RecordsInterface

        records = Records(
            [
                Record({
                    COLUMN_NAME.RCLCPP_PUBLISH_TIMESTAMP: 1,
                    'rclcpp_inter_publish_timestamp': 1,
                    COLUMN_NAME.DDS_WRITE_TIMESTAMP: 2,
                    COLUMN_NAME.RCL_PUBLISH_TIMESTAMP: 3,
                    COLUMN_NAME.PUBLISHER_HANDLE: pub_handle,
                    COLUMN_NAME.MESSAGE_TIMESTAMP: 8,
                }),
                Record({
                    COLUMN_NAME.RCLCPP_PUBLISH_TIMESTAMP: 2,
                    'rclcpp_inter_publish_timestamp': 2,
                    COLUMN_NAME.DDS_WRITE_TIMESTAMP: 3,
                    COLUMN_NAME.RCL_PUBLISH_TIMESTAMP: 4,
                    COLUMN_NAME.PUBLISHER_HANDLE: pub_handle + 999,
                    COLUMN_NAME.MESSAGE_TIMESTAMP: 9,
                }),
                Record({
                    COLUMN_NAME.RCLCPP_PUBLISH_TIMESTAMP: 3,
                    'rclcpp_inter_publish_timestamp': 3,
                    COLUMN_NAME.DDS_WRITE_TIMESTAMP: 4,
                    COLUMN_NAME.RCL_PUBLISH_TIMESTAMP: 5,
                    COLUMN_NAME.PUBLISHER_HANDLE: pub_handle,
                    COLUMN_NAME.MESSAGE_TIMESTAMP: 9,
                })
            ],
            [
                COLUMN_NAME.PUBLISHER_HANDLE,
                'rclcpp_publish_timestamp',
                'rclcpp_inter_publish_timestamp',
                COLUMN_NAME.DDS_WRITE_TIMESTAMP,
                COLUMN_NAME.RCL_PUBLISH_TIMESTAMP,
                COLUMN_NAME.RCLCPP_INTRA_PUBLISH_TIMESTAMP,
                COLUMN_NAME.MESSAGE_TIMESTAMP,
                COLUMN_NAME.SOURCE_TIMESTAMP,
            ]
        )

        helper_mock = mocker.Mock(spec=RecordsProviderLttngHelper)
        mocker.patch(
            'caret_analyze.infra.lttng.records_provider_lttng.RecordsProviderLttngHelper',
            return_value=helper_mock)
        mocker.patch.object(helper_mock, 'get_subscription_callback_object_inter',
                            return_value=cb_object)
        mocker.patch.object(helper_mock, 'get_publisher_handles',
                            return_value=[pub_handle])

        mocker.patch.object(
            lttng_mock, 'compose_publish_records', return_value=records)
        provider = RecordsProviderLttng(lttng_mock)

        mocker.patch.object(pub_mock, 'topic_name', '/topic')

        records = provider.publish_records(pub_mock)
        assert len(records.data) == 2

    def test_get_rmw_impl(self, mocker: MockerFixture):
        lttng_mock = mocker.Mock(spec=Lttng)
        mocker.patch.object(
            lttng_mock, 'get_rmw_impl', return_value='rmw')
        provider = RecordsProviderLttng(lttng_mock)

        assert provider.get_rmw_implementation() == 'rmw'

    def test_intra_proc_comm_records(self, mocker: MockerFixture):
        lttng_mock = mocker.Mock(spec=Lttng)

        comm_mock = mocker.Mock(spec=CommunicationStructValue)
        pub_mock = mocker.Mock(spec=PublisherStructValue)
        sub_cb_mock = mocker.Mock(spec=SubscriptionCallbackStructValue)

        cb_object = 5
        pub_handle = 6

        records: RecordsInterface

        records = Records(
            [
                Record({
                    COLUMN_NAME.RCLCPP_INTRA_PUBLISH_TIMESTAMP: 1,
                    COLUMN_NAME.CALLBACK_START_TIMESTAMP: 2,
                    COLUMN_NAME.PUBLISHER_HANDLE: pub_handle,
                    COLUMN_NAME.CALLBACK_OBJECT: cb_object,
                    COLUMN_NAME.MESSAGE_TIMESTAMP: 7,
                }),
                Record({
                    COLUMN_NAME.RCLCPP_INTRA_PUBLISH_TIMESTAMP: 2,
                    COLUMN_NAME.CALLBACK_START_TIMESTAMP: 3,
                    COLUMN_NAME.PUBLISHER_HANDLE: pub_handle + 999,
                    COLUMN_NAME.CALLBACK_OBJECT: cb_object,
                    COLUMN_NAME.MESSAGE_TIMESTAMP: 8,
                }),
                Record({
                    COLUMN_NAME.RCLCPP_INTRA_PUBLISH_TIMESTAMP: 3,
                    COLUMN_NAME.CALLBACK_START_TIMESTAMP: 4,
                    COLUMN_NAME.PUBLISHER_HANDLE: pub_handle,
                    COLUMN_NAME.CALLBACK_OBJECT: cb_object + 999,
                    COLUMN_NAME.MESSAGE_TIMESTAMP: 9,
                })
            ],
            [
                COLUMN_NAME.PUBLISHER_HANDLE,
                COLUMN_NAME.CALLBACK_OBJECT,
                COLUMN_NAME.RCLCPP_INTRA_PUBLISH_TIMESTAMP,
                COLUMN_NAME.CALLBACK_START_TIMESTAMP,
                COLUMN_NAME.MESSAGE_TIMESTAMP
            ]
        )

        mocker.patch.object(comm_mock, 'publisher', pub_mock)
        mocker.patch.object(comm_mock, 'subscribe_callback', sub_cb_mock)

        helper_mock = mocker.Mock(spec=RecordsProviderLttngHelper)
        mocker.patch(
            'caret_analyze.infra.lttng.records_provider_lttng.RecordsProviderLttngHelper',
            return_value=helper_mock)
        mocker.patch.object(helper_mock, 'get_subscription_callback_object_intra',
                            return_value=cb_object)
        mocker.patch.object(helper_mock, 'get_publisher_handles',
                            return_value=[pub_handle])

        mocker.patch.object(
            lttng_mock, 'compose_intra_proc_comm_records', return_value=records)
        provider = RecordsProviderLttng(lttng_mock)

        records = provider._compose_intra_proc_comm_records(comm_mock)
        assert len(records.data) == 1

    def test_is_intra_process_communication(self, mocker: MockerFixture):
        lttng_mock = mocker.Mock(spec=Lttng)
        provider = RecordsProviderLttng(lttng_mock)
        comm_info_mock = mocker.Mock(spec=Lttng)

        records = Records()
        mocker.patch.object(
            provider, '_compose_intra_proc_comm_records', return_value=records)
        assert provider.is_intra_process_communication(comm_info_mock) is False
        records.concat(Records([Record()]))

        assert provider.is_intra_process_communication(comm_info_mock) is True


class TestRecordsProviderLttngHelper:

    def test_get_callback_objects_timer_callback(self, mocker: MockerFixture):
        lttng_mock = mocker.Mock(spec=Lttng)
        timer_cb_info_mock = mocker.Mock(spec=TimerCallbackStructValue)
        cb_info_mock = mocker.Mock(spec=TimerCallbackValueLttng)

        callback_object = 3

        lttng_bridge_mock = mocker.Mock(spec=LttngBridge)
        mocker.patch('caret_analyze.infra.lttng.bridge.LttngBridge',
                     return_value=lttng_bridge_mock)
        mocker.patch.object(
            lttng_bridge_mock, 'get_timer_callback', return_value=cb_info_mock)
        mocker.patch.object(cb_info_mock, 'callback_object', callback_object)

        helper = RecordsProviderLttngHelper(lttng_mock)

        objs = helper.get_callback_objects(timer_cb_info_mock)
        assert objs == [callback_object]

    def test_get_callback_objects_subscription_callback(self, mocker: MockerFixture):
        lttng_mock = mocker.Mock(spec=Lttng)
        timer_cb_info_mock = mocker.Mock(spec=TimerCallbackStructValue)
        cb_info_mock = mocker.Mock(spec=TimerCallbackValueLttng)

        callback_object = 3

        lttng_bridge_mock = mocker.Mock(spec=LttngBridge)
        mocker.patch('caret_analyze.infra.lttng.bridge.LttngBridge',
                     return_value=lttng_bridge_mock)
        mocker.patch.object(
            lttng_bridge_mock, 'get_timer_callback', return_value=cb_info_mock)
        mocker.patch.object(cb_info_mock, 'callback_object', callback_object)

        helper = RecordsProviderLttngHelper(lttng_mock)

        objs = helper.get_callback_objects(timer_cb_info_mock)
        assert objs == [callback_object]

    def test_get_timer_callback_object(self, mocker: MockerFixture):
        lttng_mock = mocker.Mock(spec=Lttng)
        sub_cb_info_mock = mocker.Mock(spec=SubscriptionCallbackStructValue)
        cb_info_mock = mocker.Mock(spec=SubscriptionCallbackValueLttng)

        callback_object = 3
        callback_object_intra = 4

        lttng_bridge_mock = mocker.Mock(spec=LttngBridge)
        mocker.patch('caret_analyze.infra.lttng.bridge.LttngBridge',
                     return_value=lttng_bridge_mock)
        mocker.patch.object(
            lttng_bridge_mock, 'get_subscription_callback', return_value=cb_info_mock)
        mocker.patch.object(cb_info_mock, 'callback_object', callback_object)
        mocker.patch.object(cb_info_mock, 'callback_object_intra', callback_object_intra)
        helper = RecordsProviderLttngHelper(lttng_mock)

        objs = helper.get_callback_objects(sub_cb_info_mock)
        assert objs == [callback_object, callback_object_intra]

    def test_get_subscription_callback_object(self, mocker: MockerFixture):
        lttng_mock = mocker.Mock(spec=Lttng)
        sub_cb_info_mock = mocker.Mock(spec=SubscriptionCallbackStructValue)
        cb_info_mock = mocker.Mock(spec=SubscriptionCallbackValueLttng)

        callback_object = 3

        lttng_bridge_mock = mocker.Mock(spec=LttngBridge)
        mocker.patch('caret_analyze.infra.lttng.bridge.LttngBridge',
                     return_value=lttng_bridge_mock)
        mocker.patch.object(
            lttng_bridge_mock, 'get_subscription_callback', return_value=cb_info_mock)
        mocker.patch.object(cb_info_mock, 'callback_object', callback_object)

        helper = RecordsProviderLttngHelper(lttng_mock)

        obj = helper.get_subscription_callback_object_inter(sub_cb_info_mock)
        assert obj == callback_object

    def test_get_subscription_callback_object_intra(self, mocker: MockerFixture):
        lttng_mock = mocker.Mock(spec=Lttng)
        sub_cb_info_mock = mocker.Mock(spec=SubscriptionCallbackStructValue)
        cb_info_mock = mocker.Mock(spec=SubscriptionCallbackValueLttng)

        callback_object = 3

        lttng_bridge_mock = mocker.Mock(spec=LttngBridge)
        mocker.patch('caret_analyze.infra.lttng.bridge.LttngBridge',
                     return_value=lttng_bridge_mock)
        mocker.patch.object(
            lttng_bridge_mock, 'get_subscription_callback', return_value=cb_info_mock)
        mocker.patch.object(cb_info_mock, 'callback_object_intra', callback_object)

        helper = RecordsProviderLttngHelper(lttng_mock)

        obj = helper.get_subscription_callback_object_intra(sub_cb_info_mock)
        assert obj == callback_object

    def test_get_publisher_handles(self, mocker: MockerFixture):
        lttng_mock = mocker.Mock(spec=Lttng)

        pub_handle = 3

        lttng_bridge_mock = mocker.Mock(spec=LttngBridge)
        mocker.patch('caret_analyze.infra.lttng.bridge.LttngBridge',
                     return_value=lttng_bridge_mock)
        helper = RecordsProviderLttngHelper(lttng_mock)

        pub_info_mock = mocker.Mock(spec=PublisherStructValue)

        pub_info_lttng_mock = mocker.Mock(spec=PublisherValueLttng)
        mocker.patch.object(pub_info_lttng_mock,
                            'publisher_handle', pub_handle)
        mocker.patch.object(lttng_bridge_mock, 'get_publishers', return_value=[
                            pub_info_lttng_mock])
        pub_handles = helper.get_publisher_handles(pub_info_mock)
        assert pub_handles == [pub_handle]


class TestNodeRecordsCallbackChain:

    def test_single_callback(self, mocker: MockerFixture):
        provider_mock = mocker.Mock(spec=RecordsProviderLttng)
        path_info_mock = mocker.Mock(spec=NodePathStructValue)
        cb_info_mock = mocker.Mock(spec=CallbackStructValue)

        records_data: List[RecordInterface]
        records_data = [
            Record({
                COLUMN_NAME.CALLBACK_START_TIMESTAMP: 0,
                COLUMN_NAME.CALLBACK_END_TIMESTAMP: 1,
            }),
            Record({
                COLUMN_NAME.CALLBACK_START_TIMESTAMP: 2,
                COLUMN_NAME.CALLBACK_END_TIMESTAMP: 3,
            }),
        ]
        cb_records = Records(
            records_data,
            [
                COLUMN_NAME.CALLBACK_START_TIMESTAMP,
                COLUMN_NAME.CALLBACK_END_TIMESTAMP,
            ]
        )
        mocker.patch.object(provider_mock, 'callback_records', return_value=cb_records)
        mocker.patch.object(path_info_mock, 'callbacks', return_value=[cb_info_mock])
        mocker.patch.object(cb_info_mock, 'publish_topic_names', None)
        mocker.patch.object(cb_info_mock, 'callback_name', 'cb')
        mocker.patch.object(cb_info_mock, 'node_name', 'node')
        mocker.patch.object(path_info_mock, 'publish_topic_name', None)
        mocker.patch.object(path_info_mock, 'publisher', None)
        mocker.patch.object(path_info_mock, 'subscribe_topic_name', None)
        mocker.patch.object(path_info_mock, 'child', [cb_info_mock])
        callback_chain = mocker.Mock(spec=CallbackChain)
        mocker.patch.object(path_info_mock, 'message_context', callback_chain)

        # to_records changes the column name of cb_records,
        # so create expect before execution.
        expect = cb_records.clone()

        node_records = NodeRecordsCallbackChain(provider_mock, path_info_mock)

        records = node_records.to_records()
        assert records.equals(expect)

    def test_single_variable_passing(self, mocker: MockerFixture):
        provider_mock = mocker.Mock(spec=RecordsProviderLttng)
        path_info_mock = mocker.Mock(spec=NodePathStructValue)
        vp_info_mock = mocker.Mock(spec=VariablePassingStructValue)

        records_data: List[RecordInterface]
        records_data = [
                Record({
                    COLUMN_NAME.CALLBACK_END_TIMESTAMP: 1,
                    COLUMN_NAME.CALLBACK_START_TIMESTAMP: 2,
                }),
                Record({
                    COLUMN_NAME.CALLBACK_END_TIMESTAMP: 3,
                    COLUMN_NAME.CALLBACK_START_TIMESTAMP: 4,
                }),
            ]
        vp_records = Records(
            records_data,
            [
                COLUMN_NAME.CALLBACK_END_TIMESTAMP,
                COLUMN_NAME.CALLBACK_START_TIMESTAMP,
            ]
        )
        mocker.patch.object(provider_mock, 'variable_passing_records', return_value=vp_records)
        mocker.patch.object(path_info_mock, 'callbacks', return_value=[])
        mocker.patch.object(path_info_mock, 'publish_topic_name', None)
        mocker.patch.object(path_info_mock, 'publisher', None)
        mocker.patch.object(path_info_mock, 'subscribe_topic_name', None)
        mocker.patch.object(path_info_mock, 'child', [vp_info_mock])
        callback_chain = mocker.Mock(spec=CallbackChain)
        mocker.patch.object(path_info_mock, 'message_context', callback_chain)

        cb_write_mock = mocker.Mock(spec=CallbackStructValue)
        cb_read_mock = mocker.Mock(spec=CallbackStructValue)
        mocker.patch.object(cb_write_mock, 'callback_name', 'cb0')
        mocker.patch.object(cb_write_mock, 'node_name', 'node')
        mocker.patch.object(cb_read_mock, 'callback_name', 'cb1')
        mocker.patch.object(cb_read_mock, 'node_name', 'node')
        mocker.patch.object(vp_info_mock, 'callback_write', cb_write_mock)
        mocker.patch.object(vp_info_mock, 'callback_read', cb_read_mock)

        # to_records changes the column name of cb_records,
        # so create expect before execution.
        expect = vp_records.clone()

        node_records = NodeRecordsCallbackChain(provider_mock, path_info_mock)
        records = node_records.to_records()
        assert records.equals(expect)

    def test_multi_callback(self, mocker: MockerFixture):
        provider_mock = mocker.Mock(spec=RecordsProviderLttng)
        path_info_mock = mocker.Mock(spec=NodePathStructValue)

        vp_info_mock = mocker.Mock(spec=VariablePassingStructValue)
        cb0_info_mock = mocker.Mock(spec=CallbackStructValue)
        cb1_info_mock = mocker.Mock(spec=CallbackStructValue)

        cb0_records = Records(
            [
                Record({
                    f'cb0/{COLUMN_NAME.CALLBACK_START_TIMESTAMP}': 0,
                    f'cb0/{COLUMN_NAME.CALLBACK_END_TIMESTAMP}': 1,
                }),
                Record({
                    f'cb0/{COLUMN_NAME.CALLBACK_START_TIMESTAMP}': 2,
                    f'cb0/{COLUMN_NAME.CALLBACK_END_TIMESTAMP}': 3,
                }),
            ],
            [
                f'cb0/{COLUMN_NAME.CALLBACK_START_TIMESTAMP}',
                f'cb0/{COLUMN_NAME.CALLBACK_END_TIMESTAMP}',
            ]
        )
        vp_records = Records(
            [
                Record({
                    f'cb0/{COLUMN_NAME.CALLBACK_END_TIMESTAMP}': 1,
                    f'cb1/{COLUMN_NAME.CALLBACK_START_TIMESTAMP}': 2,
                }),
                Record({
                    f'cb0/{COLUMN_NAME.CALLBACK_END_TIMESTAMP}': 3,
                    f'cb1/{COLUMN_NAME.CALLBACK_START_TIMESTAMP}': 4,
                }),
            ],
            [
                f'cb0/{COLUMN_NAME.CALLBACK_END_TIMESTAMP}',
                f'cb1/{COLUMN_NAME.CALLBACK_START_TIMESTAMP}',
            ]
        )
        cb1_records = Records(
            [
                Record({
                    f'cb1/{COLUMN_NAME.CALLBACK_START_TIMESTAMP}': 2,
                    f'cb1/{COLUMN_NAME.CALLBACK_END_TIMESTAMP}': 3,
                }),
                Record({
                    f'cb1/{COLUMN_NAME.CALLBACK_START_TIMESTAMP}': 4,
                    f'cb1/{COLUMN_NAME.CALLBACK_END_TIMESTAMP}': 5,
                }),
            ],
            [
                f'cb1/{COLUMN_NAME.CALLBACK_START_TIMESTAMP}',
                f'cb1/{COLUMN_NAME.CALLBACK_END_TIMESTAMP}',
            ]
        )

        def callback_records(callback_info: CallbackStructValue):
            if callback_info == cb0_info_mock:
                return cb0_records
            return cb1_records

        mocker.patch.object(provider_mock, 'callback_records', side_effect=callback_records)
        mocker.patch.object(provider_mock, 'variable_passing_records', return_value=vp_records)
        mocker.patch.object(path_info_mock, 'callbacks', return_value=[vp_info_mock])
        mocker.patch.object(path_info_mock, 'publish_topic_name', None)
        mocker.patch.object(path_info_mock, 'publisher', None)
        mocker.patch.object(path_info_mock, 'subscribe_topic_name', None)
        mocker.patch.object(
            path_info_mock, 'child', [cb0_info_mock, vp_info_mock, cb1_info_mock])
        callback_chain = mocker.Mock(spec=CallbackChain)
        mocker.patch.object(path_info_mock, 'message_context', callback_chain)

        mocker.patch.object(cb0_info_mock, 'node_name', 'node')
        mocker.patch.object(cb1_info_mock, 'node_name', 'node')
        mocker.patch.object(cb0_info_mock, 'callback_name', 'cb0')
        mocker.patch.object(cb1_info_mock, 'callback_name', 'cb1')

        mocker.patch.object(vp_info_mock, 'callback_write', cb0_info_mock)
        mocker.patch.object(vp_info_mock, 'callback_read', cb1_info_mock)

        node_records = NodeRecordsCallbackChain(provider_mock, path_info_mock)

        column_names = [
            InfraHelper.cb_to_column(cb0_info_mock, COLUMN_NAME.CALLBACK_START_TIMESTAMP),
            InfraHelper.cb_to_column(cb0_info_mock, COLUMN_NAME.CALLBACK_END_TIMESTAMP),
            InfraHelper.cb_to_column(cb1_info_mock, COLUMN_NAME.CALLBACK_START_TIMESTAMP),
            InfraHelper.cb_to_column(cb1_info_mock, COLUMN_NAME.CALLBACK_END_TIMESTAMP),
        ]
        records = node_records.to_records()
        expect = Records(
            [
                Record({
                    column_names[0]: 0,
                    column_names[1]: 1,
                    column_names[2]: 2,
                    column_names[3]: 3,
                }),
                Record({
                    column_names[0]: 2,
                    column_names[1]: 3,
                    column_names[2]: 4,
                    column_names[3]: 5,
                }),
            ],
            column_names
        )
        assert records.equals(expect)