from pathlib import Path
from datetime import datetime

from ..processes import ProcessHandler


class PyTorchCppProcess(ProcessHandler):
    benchmark_app_name = 'pytorch_cpp_benchmark'
    launcher_latency_units = 'milliseconds'

    def __init__(self, test, executor, log, cpp_benchmarks_dir):
        super().__init__(test, executor, log)

        invalid_path_exception = ValueError('Must provide valid path to the folder '
                                            'with PyTorch Cpp benchmark (--cpp_benchmarks_dir)')
        if not cpp_benchmarks_dir:
            raise invalid_path_exception

        if self._test.dep_parameters.tensor_rt_precision:
            if self._test.dep_parameters.tensor_rt_precision == 'FP32':
                self._benchmark_path = Path(cpp_benchmarks_dir).joinpath('pytorch_tensorrt_benchmark')
            else:
                raise ValueError('Unknown TensorRT precision')
        else:
            self._benchmark_path = Path(cpp_benchmarks_dir).joinpath('pytorch_benchmark')

        if not self._benchmark_path.is_file():
            raise invalid_path_exception

        self._report_path = executor.get_path_to_logs_folder().joinpath(
            f'pytorch_benchmark_{test.model.name}_{datetime.now().strftime("%d.%m.%y_%H:%M:%S")}.json')

    @staticmethod
    def create_process(test, executor, log, cpp_benchmarks_dir):
        return PyTorchCppProcess(test, executor, log, cpp_benchmarks_dir)

    def get_performance_metrics(self):
        return self.get_performance_metrics_from_json_report()

    def _fill_command_line(self):
        return self._fill_command_line_cpp()
