from ..config_parser.dependent_parameters_parser import DependentParametersParser
from ..config_parser.framework_parameters_parser import FrameworkParameters

class TVMParametersParser(DependentParametersParser):
    def parse_parameters(self, curr_test):
        CONFIG_FRAMEWORK_DEPENDENT_TAG = 'FrameworkDependent'
        CONFIG_FRAMEWORK_DEPENDENT_NAME_OF_FRAMEWORK_TAG = 'Framework'
        CONFIG_FRAMEWORK_DEPENDENT_INPUT_NAME_TAG = 'InputName'
        CONFIG_FRAMEWORK_DEPENDENT_INPUT_SHAPE_TAG = 'InputShape'
        CONFIG_FRAMEWORK_DEPENDENT_NORMALIZE_TAG = 'Normalize'
        CONFIG_FRAMEWORK_DEPENDENT_MEAN_TAG = 'Mean'
        CONFIG_FRAMEWORK_DEPENDENT_STD_TAG = 'Std'
        CONFIG_FRAMEWORK_DEPENDENT_CHANNEL_SWAP_TAG = 'ChannelSwap'

        dep_parameters_tag = curr_test.getElementsByTagName(CONFIG_FRAMEWORK_DEPENDENT_TAG)[0]

        _framework = dep_parameters_tag.getElementsByTagName(
            CONFIG_FRAMEWORK_DEPENDENT_NAME_OF_FRAMEWORK_TAG)[0].firstChild
        _input_name = dep_parameters_tag.getElementsByTagName(
            CONFIG_FRAMEWORK_DEPENDENT_INPUT_NAME_TAG)[0].firstChild
        _input_shape = dep_parameters_tag.getElementsByTagName(
            CONFIG_FRAMEWORK_DEPENDENT_INPUT_SHAPE_TAG)[0].firstChild
        _normalize = dep_parameters_tag.getElementsByTagName(
            CONFIG_FRAMEWORK_DEPENDENT_NORMALIZE_TAG)[0].firstChild
        _mean = dep_parameters_tag.getElementsByTagName(
            CONFIG_FRAMEWORK_DEPENDENT_MEAN_TAG)[0].firstChild
        _std = dep_parameters_tag.getElementsByTagName(
            CONFIG_FRAMEWORK_DEPENDENT_STD_TAG)[0].firstChild
        _channel_swap = dep_parameters_tag.getElementsByTagName(
            CONFIG_FRAMEWORK_DEPENDENT_CHANNEL_SWAP_TAG)[0].firstChild


class TVMParameters(FrameworkParameters):
    def __init__(self, framework, input_name, input_shape,
                 normalize, mean, std, channel_swap):
        self.framework = None
        self.input_name = None
        self.input_shape = None
        self.normalize = None
        self.mean = None
        self.std = None
        self.channel_swap = None

        if self._framework_is_correct(framework):
            self.framework = framework
        if self._parameter_is_not_none(input_name):
            self.input_name = input_name
        if self._parameter_is_not_none(input_shape):
            self.input_shape = input_shape
        if self._parameter_is_not_none(normalize):
            self.normalize = normalize
        if self._parameter_is_not_none(mean):
            self.mean = mean
        if self._parameter_is_not_none(std):
            self.std = std
        if self._parameter_is_not_none(channel_swap):
            self.channel_swap = channel_swap

    @staticmethod
    def _framework_is_correct(framework):
        correct_frameworks = ['mxnet', 'onnx', 'tvm',
                              'tf', 'tflite', 'pytorch']
        if framework.lower() in correct_frameworks:
            return True
        else:
            raise ValueError(f'Framework is required parameter. TVM support: {", ".join(correct_frameworks)}')