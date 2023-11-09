from scipy.special import softmax
from time import time

from inference_tools.loop_tools import loop_inference, get_exec_time


def create_dict_for_converter_mxnet(args):
    dictionary = {
        'input_name': args.input_name,
        'input_shape': [args.batch_size] + args.input_shape[1:4],
        'model_name': args.model_name,
        'model_path': args.model_path,
        'model_params': args.model_params,
        'device': args.device,
        'opt_level': args.opt_level,
    }
    return dictionary


def create_dict_for_converter_tvm(args):
    return create_dict_for_converter_mxnet(args)


def create_dict_for_converter_pytorch(args):
    dictionary = {
        'input_name': args.input_name,
        'input_shape': [args.batch_size] + args.input_shape[1:4],
        'model_name': args.model_name,
        'model_path': args.model_path,
        'model_params': args.model_params,
        'device': args.device,
        'opt_level': args.opt_level,
        'module': args.module,
    }
    return dictionary


def create_dict_for_converter_onnx(args):
    dictionary = {
        'input_name': args.input_name,
        'input_shape': [args.batch_size] + args.input_shape[1:4],
        'model_name': args.model_name,
        'model_path': args.model_path,
        'device': args.device,
        'opt_level': args.opt_level,
    }
    return dictionary


def create_dict_for_transformer(args):
    dictionary = {
        'channel_swap': args.channel_swap,
        'mean': args.mean,
        'std': args.std,
        'norm': args.norm,
        'input_shape': args.input_shape,
        'batch_size': args.batch_size,
    }
    return dictionary


def create_dict_for_modelwrapper(args):
    dictionary = {
        'input_name': args.input_name,
        'input_shape': [args.batch_size] + args.input_shape[1:4],
        'model_name': args.model_name,
    }
    return dictionary


def inference_tvm(module, num_of_iterations, input_name, get_slice, test_duration):
    result = None
    time_infer = []
    if num_of_iterations == 1:
        slice_input = get_slice()
        t0 = time()
        module.set_input(input_name, slice_input[input_name])
        module.run()
        result = module.get_output(0)
        t1 = time()
        time_infer.append(t1 - t0)
    else:
        time_infer = loop_inference(num_of_iterations, test_duration)(inference_iteration)(get_slice,
                                                                                           input_name,
                                                                                           module)
    return result, time_infer


def inference_iteration(get_slice, input_name, module):
    slice_input = get_slice()
    _, exec_time = infer_slice(input_name, module, slice_input)
    return exec_time


@get_exec_time()
def infer_slice(input_name, module, slice_input):
    module.set_input(input_name, slice_input[input_name])
    module.run()
    res = module.get_output(0)
    return res


def prepare_output(result, task, output_names):
    if task == 'feedforward':
        return {}
    if task == 'classification':
        return {output_names[0]: softmax(result.asnumpy())}
