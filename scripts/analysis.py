# copyright (c) 2019 PaddlePaddle Authors. All Rights Reserve.
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

from __future__ import print_function

import argparse
import json


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--filename", type=str, help="The name of log which need to analysis.")
    parser.add_argument(
        "--keyword", type=str, help="Keyword to specify analysis data")
    parser.add_argument(
        "--separator", type=str, default=" ", help="Separator of different field in log")
    parser.add_argument(
        '--position', type=int, default=-1, help='The position of data field')
    parser.add_argument(
        '--range', type=int, default=0, help='The range of data field to intercept')
    parser.add_argument(
        '--base_batch_size', type=int, help='base_batch size on gpu')
    parser.add_argument(
        '--skip_steps', type=int, default=0, help='The number of steps to be skipped')
    parser.add_argument(
        '--model_mode', type=int, default=0, help='Analysis mode, 0')
    parser.add_argument(
        '--model_name', type=str, default=0, help='training model_name, transformer_base')
    parser.add_argument(
        '--run_mode', type=str, default="sp", help='multi process or single process')
    parser.add_argument(
        '--index', type=str, default="speed", help='speed | maxbs | mem')
    parser.add_argument(
        '--gpu_num', type=int, default=1, help='nums of training gpus')
    args = parser.parse_args()
    return args


class TimeAnalyzer(object):
    def __init__(self, filename, keyword=None, separator=" ", position=-1, range=-1):
        if filename is None:
            raise Exception("Please specify the filename!")

        if keyword is None:
            raise Exception("Please specify the keyword!")

        self.filename = filename
        self.keyword = keyword
        self.separator = separator
        self.position = position
        self.range = range
        self.records = None
        self._distil()

    def _distil(self):
        self.records = []
        with open(self.filename, "r") as f_object:
            lines = f_object.readlines()
            for line in lines:
                if self.keyword not in line:
                    continue
                try:
                    line = line.strip()
                    result = line.split("" if not self.separator else self.separator)[self.position]
                    result = result[0:] if not self.range else result[0:self.range]
                    self.records.append(float(result))
                except Exception as exc:
                    print("line is: {}; separator={}; position={}".format(line, self.separator, self.position))

    def analysis(self, batch_size, gpu_num=1, skip_steps=0, mode=0):
        if batch_size <= 0:
            print("FINAL_RESULT={:.3f}".format(0.0))
            print("base_batch_size should larger than 0.")
            return

        if len(self.records) <= 0:
            print("FINAL_RESULT={:.3f}".format(0.0))
            print("no records")
            return

        sum_of_records = 0
        sum_of_records_skipped = 0
        skip_min = self.records[skip_steps]
        skip_max = self.records[skip_steps]

        count = len(self.records)
        for i in range(count):
            sum_of_records += self.records[i]
            if i >= skip_steps:
                sum_of_records_skipped += self.records[i]
                if self.records[i] < skip_min:
                    skip_min = self.records[i]
                if self.records[i] > skip_max:
                    skip_max = self.records[i]

        avg_of_records = sum_of_records / float(count)
        avg_of_records_skipped = sum_of_records_skipped / float(count - skip_steps)

        if mode == 1:
            final_result = avg_of_records_skipped
            print("average latency of %d steps, skip 0 step:" % count)
            print("\tAvg: %.3f steps/s" % avg_of_records)
            print("\tFPS: %.3f samples/s" % (batch_size * gpu_num * avg_of_records))
            if skip_steps > 0:
                print("average latency of %d steps, skip %d steps:" % (count, skip_steps))
                print("\tAvg: %.3f steps/s" % avg_of_records_skipped)
                print("\tMin: %.3f steps/s" % skip_min)
                print("\tMax: %.3f steps/s" % skip_max)
                print("\tFPS: %.3f samples/s" % (batch_size * gpu_num * avg_of_records_skipped))
        else:
            final_result = (batch_size * gpu_num) / avg_of_records_skipped
            print("average latency of %d steps, skip 0 step:" % count)
            print("\tAvg: %.3f s/step" % avg_of_records)
            print("\tFPS: %.3f samples/s" % (batch_size * gpu_num / avg_of_records))
            if skip_steps > 0:
                print("average latency of %d steps, skip %d steps:" % (count, skip_steps))
                print("\tAvg: %.3f s/step" % avg_of_records_skipped)
                print("\tMin: %.3f s/step" % skip_min)
                print("\tMax: %.3f s/step" % skip_max)
                print("\tFPS: %.3f samples/s" % final_result)

        print("FINAL_RESULT={:.3f}".format(final_result))


if __name__ == "__main__":
    args = parse_args()
    run_info = dict()
    run_info["log_file"] = args.filename
    run_info["model_name"] = args.model_name
    run_info["run_mode"] = args.run_mode
    run_info["index"] = args.index
    run_info["gpu_num"] = args.gpu_num

    analyzer = TimeAnalyzer(args.filename, args.keyword, args.separator, args.position, args.range)
    analyzer.analysis(args.base_batch_size, args.gpu_num, args.skip_steps, args.model_mode)
    print("{}".format(json.dumps(run_info)))  # it's required, for the log file path  insert to the database
