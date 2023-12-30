import importlib
import abc
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent.joinpath('utils')))
from logger_conf import configure_logger  # noqa: E402

log = configure_logger()


class Converter(metaclass=abc.ABCMeta):
    def __init__(self, args):
        self.args = args
        self.graph = None
        self.mod = None
        self.params = None
        self.mod_type = None
        self.params_type = None
        self.framework = 'tvm'
        self.tvm = importlib.import_module('tvm')
        self.graph_executor = importlib.import_module('tvm.contrib.graph_executor')

    @abc.abstractmethod
    def _get_device_for_framework(self):
        pass

    @abc.abstractmethod
    def _convert_model_from_framework(self, target, dev):
        pass

    def _get_target_device(self, task='Inference'):
        device = self.args['device']
        target_str = self.args['target']
        if device == 'CPU':
            log.info(f'{task} will be executed on {device}')
            try:
                target = self.tvm.target.Target(target_str)
            except AttributeError:
                target = None
            dev = self.tvm.cpu(0)
        else:
            raise ValueError(f'Device {device} is not supported. Supported devices: CPU')
        return target, dev

    def get_tvm_model(self):
        target, dev = self._get_target_device()
        log.info(f'Get TVM model from {self.framework} model')
        self.mod, self.params = self._convert_model_from_framework(target, dev)
        return self.mod, self.params

    def save_tvm_model(self):
        model_name = self.args['model_name']
        path_save_model = self.args['output_dir']

        if path_save_model is None:
            path_save_model = os.getcwd()

        log.info(f'Saving model \"{model_name}\" to \"{path_save_model}\"')
        if not os.path.exists(path_save_model):
            os.mkdir(path_save_model)

        log.info(f'Saving weights of the model {model_name}')
        with open(f'{path_save_model}/{model_name}.params', 'wb') as fo:
            fo.write(self.tvm.relay.save_param_dict(self.params))

        log.info(f'Saving model {model_name}')
        with open(f'{path_save_model}/{model_name}.json', 'w') as fo:
            fo.write(self.tvm.ir.save_json(self.mod))

    def get_graph_module_from_lib(self, lib):
        _, dev = self._get_target_device()
        self.graph = self.graph_executor.GraphModule(lib['default'](dev))
        return self.graph

    def get_lib(self):
        target, dev = self._get_target_device()
        model = self._convert_model_from_framework(target, dev)

        log.info('Model compilation')
        if self.args['vm']:
            rly_vm = self.tvm.relay.vm
            with self.tvm.transform.PassContext(opt_level=self.args['opt_level']):
                executable = rly_vm.compile(model[0], target=target, params=model[1])
            code, lib = executable.save()
            return code, lib
        else:
            with self.tvm.transform.PassContext(opt_level=self.args['opt_level']):
                lib = self.tvm.relay.build(model[0], target=target, params=model[1])
            return [lib]

    def export_lib(self):
        path_save_lib = self.args['output_dir']
        lib_name = self.args['lib_name']
        if path_save_lib is None:
            path_save_lib = os.getcwd()

        log.info(f'Saving library of model \"{lib_name}\" to \"{path_save_lib}\"')
        if not os.path.exists(path_save_lib):
            os.mkdir(path_save_lib)

        lib = self.get_lib()
        if len(lib) == 1:
            lib[0].export_library(f'{path_save_lib}/{lib_name}.so')
        else:
            lib[1].export_library(f'{path_save_lib}/{lib_name}.so')
            with open(f'{path_save_lib}/{lib_name}.ro', 'wb') as fo:
                fo.write(lib[0])

    def get_graph_module_from_vm(self, mod, params, target, dev):
        rly_vm = self.tvm.relay.vm
        vm = self.tvm.runtime.vm
        if self.mod_type == 'so' and self.params_type == 'ro':
            print('here')
            executable = vm.Executable.load_exec(params, mod)
        else:
            with self.tvm.transform.PassContext(opt_level=self.args['opt_level']):
                executable = rly_vm.compile(mod, target=target, params=params)
        des_vm = vm.VirtualMachine(executable, dev)
        return des_vm

    def get_graph_module_from_relay(self, mod, params, target, dev):
        with self.tvm.transform.PassContext(opt_level=self.args['opt_level']):
            lib = self.tvm.relay.build(mod, target=target, params=params)
        self.graph = self.graph_executor.GraphModule(lib['default'](dev))
        return self.graph       

    def get_graph_module(self):
        target, dev = self._get_target_device()
        log.info(f'Get TVM model from {self.framework} model')
        model = self._convert_model_from_framework(target, dev)

        log.info(f'Creating graph module from {self.framework} model')
        if len(model) == 2:
            if self.args['vm']:
                return self.get_graph_module_from_vm(model[0], model[1], target, dev)
            else:
                return self.get_graph_module_from_relay(model[0], model[1], target, dev)
        else:
            return self.get_graph_module_from_lib(model[0])


class PyTorchToTVMConverter(Converter):
    def __init__(self, args):
        self.torch = importlib.import_module('torch')
        super().__init__(args)
        self.framework = 'PyTorch'

    def _get_device_for_framework(self):
        return super()._get_device_for_framework()

    def __get_model_from_path(self, model_path, input_shape):
        log.info(f'Loading model from path {model_path}')
        input_data = self.torch.randn(input_shape)
        file_type = model_path.split('.')[-1]
        supported_extensions = ['pt']
        if file_type not in supported_extensions:
            raise ValueError(f'The file type {file_type} is not supported')
        model = self.torch.load(model_path)
        model = model.eval()
        scripted_model = self.torch.jit.trace(model, input_data).eval()
        return scripted_model

    def __get_model_from_module(self, model_name,
                                input_shape, weights,
                                module, device):
        log.info(f'Loading model {model_name} from module')
        input_data = self.torch.randn(input_shape)
        model_cls = importlib.import_module(module).__getattribute__(model_name)
        if weights is None or weights == '':
            log.info('Loading pretrained model')
            if self.args['model_name'] == 'maskrcnn_resnet50_fpn':
                sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
                from src.inference.configs.tvm_configs.mask_rcnn_config import TraceWrapper, do_trace
                model = TraceWrapper(model_cls(pretrained=True))
                model.eval()
                with self.torch.no_grad():
                    out = model(input_data)
                    script_module = do_trace(model, input_data)
                return script_module
            else:
                model = model_cls(weights=True)
                scripted_model = self.torch.jit.trace(model, input_data).eval()
                return scripted_model
        else:
            log.info(f'Loading model with weights from file {weights}')
            model = model_cls()
            checkpoint = self.torch.load(weights, map_location=device.lower())
            model.load_state_dict(checkpoint, strict=False)
            model = model.eval()
            scripted_model = self.torch.jit.trace(model, input_data).eval()
            return scripted_model

    def _get_pytorch_model(self):
        model_name = self.args['model_name']
        module = self.args['module']
        model_path = self.args['model_path']
        input_shape = self.args['input_shape']
        weights = self.args['model_params']
        device = self.args['device']
        if model_path is not None:
            return self.__get_model_from_path(model_path, input_shape)
        else:
            return self.__get_model_from_module(model_name, input_shape,
                                                weights, module, device)

    def _convert_model_from_framework(self, target, dev):
        input_shape = self.args['input_shape']
        scripted_model = self._get_pytorch_model()
        input_name = self.args['input_name']
        shape_list = [(input_name, input_shape)]
        model, params = self.tvm.relay.frontend.from_pytorch(scripted_model, shape_list)
        return model, params


class ONNXToTVMConverter(Converter):
    def __init__(self, args):
        self.onnx = importlib.import_module('onnx')
        super().__init__(args)
        self.framework = 'ONNX'
        self.model_onnx = None

    def _get_device_for_framework(self):
        return super()._get_device_for_framework()

    def get_input_name(self):
        return self.model_onnx.graph.input[0].name

    def _convert_model_from_framework(self, target, dev):
        model_path = self.args['model_path']
        input_shape = self.args['input_shape']
        model_onnx = self.onnx.load(model_path)
        self.model_onnx = model_onnx
        shape_dict = {model_onnx.graph.input[0].name: input_shape}
        model, params = self.tvm.relay.frontend.from_onnx(model_onnx, shape_dict)
        return model, params


class MXNetToTVMConverter(Converter):
    def __init__(self, args):
        self.mxnet = importlib.import_module('mxnet')
        self.gluoncv = importlib.import_module('gluoncv')
        super().__init__(args)
        self.framework = 'MXNet'

    def _get_device_for_framework(self):
        device = self.args['device']
        if device == 'CPU':
            return self.mxnet.cpu()
        else:
            raise ValueError(f'Device {device} is not supported. Supported devices: CPU')

    def _get_mxnet_network(self):
        model_name = self.args['model_name']
        model_path = self.args['model_path']
        weights = self.args['model_params']
        context = self._get_device_for_framework()

        if ((model_name is not None)
                and (model_path is None)
                and (weights is None)):
            log.info(f'Loading network \"{model_name}\" from GluonCV model zoo')
            net = self.gluoncv.model_zoo.get_model(model_name, pretrained=True, ctx=context)
            return net

        elif ((model_path is not None) and (weights is not None)):
            log.info(f'Deserializing network from file ({model_path}, {weights})')
            net = self.mxnet.gluon.nn.SymbolBlock.imports(
                model_path, [self.args['input_name']], weights, ctx=context)
            return net

        else:
            raise ValueError('Incorrect arguments.')

    def _convert_model_from_framework(self, target, dev):
        net = self._get_mxnet_network()
        shape_dict = {self.args['input_name']: self.args['input_shape']}
        model, params = self.tvm.relay.frontend.from_mxnet(net, shape_dict)
        return model, params


class TVMConverter(Converter):
    def __init__(self, args):
        super().__init__(args)
        self.framework = 'TVM'

    def _get_deserialized_tvm_model(self):
        model_path = self.args['model_path']
        model_params = self.args['model_params']
        with open(model_params, 'rb') as fo:
            params = self.tvm.relay.load_param_dict(fo.read())

        with open(model_path, 'r') as fo:
            mod = fo.read()

        self.mod = self.tvm.ir.load_json(mod)
        self.params = params
        return self.mod, self.params

    def _get_lib_format_tvm_model(self):
        lib = self.tvm.runtime.load_module(self.args['model_path'])
        return lib

    def _get_device_for_framework(self):
        return super()._get_device_for_framework()

    def _get_vm_format_tvm_model(self):
        lib = self.tvm.runtime.load_module(self.args['model_path'])
        code = bytearray(open(self.args['model_params'], 'rb').read())
        return lib, code

    def _convert_model_from_framework(self, target, dev):
        model_name = self.args['model_path']
        params = self.args['model_params']

        self.mod_type = model_name.split('.')[-1]
        self.params_type = params.split('.')[-1]
        if self.mod_type == 'json' and self.params_type == 'params':
            return self._get_deserialized_tvm_model()
        elif ((self.mod_type == 'so' or self.mod_type == 'tar')
              and self.params_type == None):
            return [self._get_lib_format_tvm_model()]
        elif self.mod_type == 'so' and self.params_type == 'ro':
            return self._get_vm_format_tvm_model()
        else:
            raise ValueError('Wrong arguments.')


class CaffeToTVMConverter(Converter):
    def __init__(self, args):
        self.caffe = importlib.import_module('caffe')
        super().__init__(args)
        self.text_format = importlib.import_module('google.protobuf.text_format')
        self.framework = 'Caffe'

    def _get_device_for_framework(self):
        return super()._get_device_for_framework()

    def _convert_model_from_framework(self, target, dev):
        model_path = self.args['model_path']
        model_params = self.args['model_params']
        shape_dict = {self.args['input_name']: self.args['input_shape']}
        dtype_dict = {self.args['input_name']: 'float32'}
        init_net = self.caffe.proto.caffe_pb2.NetParameter()
        predict_net = self.caffe.proto.caffe_pb2.NetParameter()

        with open(model_path, 'r') as f:
            self.text_format.Merge(f.read(), predict_net)

        with open(model_params, 'rb') as f:
            init_net.ParseFromString(f.read())

        model, params = self.tvm.relay.frontend.from_caffe(init_net,
                                                           predict_net,
                                                           shape_dict,
                                                           dtype_dict)
        return model, params


class TensorFlowLiteToTVMConverter(Converter):
    def __init__(self, args):
        self.tflite = importlib.import_module('tflite')
        super().__init__(args)
        self.framework = 'TFLite'

    def _get_device_for_framework(self):
        return super()._get_device_for_framework()

    def _get_tf_model(self, model_path):
        tflite_model_buf = open(model_path, 'rb').read()
        tflite_model = self.tflite.Model.GetRootAsModel(tflite_model_buf, 0)
        return tflite_model

    def _convert_model_from_framework(self, target, dev):
        model_path = self.args['model_path']
        model_tf = self._get_tf_model(model_path)
        shape_dict = {self.args['input_name']: self.args['input_shape']}
        dtype = {self.args['input_name']: 'float32'}
        log.info('Creating graph module from TensorFlow model')
        model, params = self.tvm.relay.frontend.from_tflite(model_tf,
                                                            shape_dict=shape_dict,
                                                            dtype_dict=dtype)
        return model, params
