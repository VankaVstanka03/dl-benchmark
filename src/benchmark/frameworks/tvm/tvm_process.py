from pathlib import Path

from ..processes import ProcessHandler


class TVMProcess(ProcessHandler):
    benchmark_app_name = 'tvm_python_benchmark'
    launcher_latency_units = 'seconds'

    def __init__(self, test, executor, log):
        super().__init__(test, executor, log)
    

    @staticmethod
    def create_process(test, executor, log):
        framework = test.dep_parameters.framework
        if framework is None:
            framework = 'TVM'
            return MXNet_TVMProcess(test, executor, log)
        else:
            framework = test.dep_parameters.framework.lower()
            if framework == 'mxnet':
                return MXNet_TVMProcess(test, executor, log)
            else:
                raise AssertionError(f'Unknown framework {framework}')

    def get_performance_metrics(self):
        return self.get_performance_metrics_from_json_report()
    
    def _fill_command_line(self):
        name = self._test.model.name
        model_json = self._test.model.model
        model_params = self._test.model.weight
        dataset = self._test.dataset.path
        input_shape = self._test.dep_parameters.input_shape
        batch_size = self._test.indep_parameters.batch_size
        iteration = self._test.indep_parameters.iteration

        if ((name is not None)
                and (model_json is None or model_json == '')
                and (model_params is None or model_params == '')):
            common_params = (f'-mn {name} -i {dataset} -is {input_shape} '
                             f'-b {batch_size} -ni {iteration} --report_path {self.report_path}')
        elif (model_json is not None) and (model_params is not None):
            common_params = (f'-m {model_json} -w {model_params} -i {dataset} '
                             f'-is {input_shape} -b {batch_size} -ni {iteration} '
                             f'--report_path {self.report_path}')
        else:
            raise Exception('Incorrect model parameters. Set model name or file names.')
        
        input_name = self._test.dep_parameters.input_name
        common_params = TVMProcess._add_optional_argument_to_cmd_line(
            common_params, '--input_name', input_name)

        normalize = self._test.dep_parameters.normalize
        if normalize == 'True':
            common_params = TVMProcess._add_flag_to_cmd_line(
                common_params, '--norm')

        mean = self._test.dep_parameters.mean
        common_params = TVMProcess._add_optional_argument_to_cmd_line(
            common_params, '--mean', mean)

        std = self._test.dep_parameters.std
        common_params = TVMProcess._add_optional_argument_to_cmd_line(
            common_params, '--std', std)

        channel_swap = self._test.dep_parameters.channel_swap
        common_params = TVMProcess._add_optional_argument_to_cmd_line(
            common_params, '--channel_swap', channel_swap)

        device = self._test.indep_parameters.device
        common_params = TVMProcess._add_optional_argument_to_cmd_line(
            common_params, '--device', device)
        
        return f'{common_params}'


class MXNet_TVMProcess(TVMProcess):
    def __init__(self, test, executor, log):
        super().__init__(test, executor, log)

    def get_performance_metrics(self):
        return self.get_performance_metrics_from_json_report()

    def _fill_command_line(self):
        path_to_sync_script = Path.joinpath(self.inference_script_root,
                                            'inference_tvm_mxnet.py')
        python = ProcessHandler.get_cmd_python_version()
        time_limit = self._test.indep_parameters.test_time_limit
        common_params = super()._fill_command_line()
        common_params += f' --time {time_limit}'
        command_line = f'{python} {path_to_sync_script} {common_params}'

        return command_line