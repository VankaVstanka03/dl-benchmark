import numpy as np


def delete_incorrect_time(time, min_correct_time):
    valid_time = []
    for i in range(len(time)):
        if time[i] >= min_correct_time:
            valid_time.append(time[i])
    return valid_time


def three_sigma_rule(time):
    average_time = np.mean(time)
    sigm = np.std(time)
    upper_bound = average_time + (3 * sigm)
    lower_bound = average_time - (3 * sigm)
    valid_time = []
    for i in range(len(time)):
        if lower_bound <= time[i] <= upper_bound:
            valid_time.append(time[i])
    return valid_time


def calculate_average_time(time):
    average_time = np.mean(time)
    return average_time


def calculate_latency(time):
    time.sort()
    latency_std = np.std(time)
    latency = np.median(time)
    return latency, latency_std


def calculate_average_fps(pictures, time):
    if time == 0:
        return -1
    return pictures / time


def calculate_performance_metrics_sync_mode(batch_size, inference_time,
                                            min_infer_time=0.0):
    first_inference_time = inference_time[0]
    execution_time = sum(inference_time)
    inference_time = delete_incorrect_time(inference_time, min_infer_time)
    inference_time = three_sigma_rule(inference_time)
    average_time = calculate_average_time(inference_time)
    latency, latency_std = calculate_latency(inference_time)
    fps = calculate_average_fps(batch_size, latency)
    inference_result = {
        'execution_time': round(execution_time, 3),
        'first_inference_time': round(first_inference_time, 5),
        'latency_avg': round(average_time, 5),
        'latency_median': round(latency, 5),
        'latency_std': round(latency_std, 5),
        'latency_max': round(max(inference_time), 5),
        'latency_min': round(min(inference_time), 5),
        'throughput': round(fps, 3),
    }
    return inference_result


def log_performance_metrics_sync_mode(log, average_time, fps, latency):
    log.info(f'Average time of single pass : {average_time:.3f}')
    log.info(f'FPS : {fps:.3f}')
    log.info(f'Latency : {latency:.3f}')


def print_performance_metrics_sync_mode(log, average_time, fps, latency):
    log.info(f'{average_time:.3f},{fps:.3f},{latency:.3f}')


def calculate_performance_metrics_async_mode(inference_time, batch_size, iteration_count):
    average_time = inference_time / iteration_count
    fps = calculate_average_fps(batch_size * iteration_count, inference_time)
    inference_result = {
        'execution_time': round(inference_time, 3),
        'latency_avg': round(average_time, 5),
        'throughput': round(fps, 3),
    }
    return inference_result


def log_performance_metrics_async_mode(log, average_time, fps):
    log.info('Average time of single pass : {0:.3f}'.format(average_time))
    log.info('FPS : {0:.3f}'.format(fps))


def print_performance_metrics_async_mode(average_time, fps):
    print('{0:.3f},{1:.3f}'.format(average_time, fps))
