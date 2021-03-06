import sys
sys.path.insert(0, '../mxnet/python')
import mxnet as mx
import math

eps = 1e-10 + 1e-5
fix_gamma = False


def ResModule(sym, base_filter, stage, first_conv, bn_mom=0.9):
    num_f = base_filter * int(math.pow(2, 2 + stage))
    stride = 1 if stage == 0 else 2

    bn1 = mx.symbol.BatchNorm(data=sym, eps=eps, fix_gamma=fix_gamma, momentum=bn_mom)
    relu1 = mx.symbol.Activation(data=bn1, act_type="relu")
    if first_conv:
        conv1 = mx.symbol.Convolution(
            data=relu1, kernel=(1, 1), stride=(stride, stride), pad=(0, 0),
            num_filter=num_f / 4)
        sym = mx.symbol.Convolution(
            data=relu1, kernel=(1, 1), stride=(stride, stride), pad=(0, 0),
            num_filter=num_f)
    else:
        conv1 = mx.symbol.Convolution(
            data=relu1, kernel=(1, 1), pad=(0, 0),
            num_filter=num_f / 4)
    bn2 = mx.symbol.BatchNorm(data=conv1, eps=eps, fix_gamma=fix_gamma, momentum=bn_mom)
    relu2 = mx.symbol.Activation(data=bn2, act_type="relu")
    conv2 = mx.symbol.Convolution(
        data=relu2, kernel=(3, 3), pad=(1, 1),
        num_filter=num_f / 4)
    bn3 = mx.symbol.BatchNorm(data=conv2, eps=eps, fix_gamma=fix_gamma, momentum=bn_mom)
    relu3 = mx.symbol.Activation(data=bn3, act_type="relu")
    conv3 = mx.symbol.Convolution(
        data=relu3, kernel=(1, 1), pad=(0, 0),
        num_filter=num_f)

    sum_sym = conv3 + sym

    return sum_sym


def get_symbol(num_classes=10, args=None):
    n = args.res_module_num
    base_filter = 16
    data = mx.symbol.Variable(name='data')
    conv1 = mx.symbol.Convolution(data=data, kernel=(
        3, 3), pad=(1, 1), num_filter=base_filter)
    sym = conv1
    for j in range(3):
        for i in range(n):
            sym = ResModule(sym, base_filter, j, i == 0)
    
    bn = mx.symbol.BatchNorm(data=sym, eps=eps, fix_gamma=fix_gamma, momentum=0.9)
    relu = mx.symbol.Activation(data=bn, act_type="tanh")

    bilinear = mx.symbol.FMConvolution3(data=relu, num_filter=num_classes, num_factor=args.fmconv_factor,
                                       kernel=(1, 1), stride=(1, 1),
                                       pad=(0, 0), p=args.fmconv_drop, name='bilinear')
    conv = mx.symbol.Convolution(
        data=relu, kernel=(1, 1), stride=(1, 1),  pad=(0, 0), num_filter=num_classes)

    pool = mx.symbol.Pooling(
         data=bilinear+conv, pool_type="avg", kernel=(8, 8), name="global_pool")
    flatten = mx.symbol.Flatten(data=pool, name="flatten1")

    net = mx.symbol.SoftmaxOutput(data=flatten, name='softmax')

    return net


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="command for training cifar")
    parser.add_argument('--res-module-num', type=int, default=18,
                        help='the number of module')
    parser.add_argument('--fmconv-factor', type=int, default=20,
                        help='the number of fmconv factor')
    parser.add_argument('--fmconv-drop', type=int, default=0.5,
                        help='fmconv drop rate')
    args = parser.parse_args()
    sym = get_symbol(10, args)
    mx.viz.print_summary(sym, {'data': (1, 3, 32, 32)})
