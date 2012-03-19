from amlpso.standardpso import StandardPSO, update_parser
from collections import defaultdict

from .conftest import run_serial, run_mockparallel, run_master_slave


def test_pso(mrs_impl, tmpdir, capfd):
    args = ['-i', '20', '-n', '5', '-d', '2', '--out-freq', '3', '--mrs-seed',
            '42', '--hey-im-testing']

    if mrs_impl == 'serial':
        run_serial(StandardPSO, args, update_parser)
    elif mrs_impl == 'mockparallel':
        run_mockparallel(StandardPSO, args, tmpdir, update_parser)
    elif mrs_impl == 'master_slave':
        run_master_slave(StandardPSO, args, tmpdir, update_parser)
    else:
        raise RuntimeError('Unknown mrs_impl: %s' % mrs_impl)

    out, err = capfd.readouterr()
    assert err == ''

    lines = [line.strip() for line in out.splitlines()
            if line and not line.startswith('#')]
    assert lines == ['202.330512851', '202.330512851', '74.0008930067',
            '32.3155678366', '2.9191713839', '2.9191713839', '2.9191713839']


# vim: et sw=4 sts=4