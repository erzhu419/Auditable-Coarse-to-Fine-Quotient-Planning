"""Frozen chronological workload and context-paired potential sampling streams."""
ORDERS = ('original', 'interleaved')
PERMUTATION = (4,0,6,1,5,2,7,3,10,8,11,9)

def original_cases(roster):
    return ([c for c in roster if c['weather']=='normal']+
            [c for c in roster if c['weather']!='normal' and c['operating']=='high']+
            [c for c in roster if c['weather']!='normal' and c['operating']=='low'])

def sequence(roster, order):
    cases=original_cases(roster)
    return cases if order=='original' else [cases[i] for i in PERMUTATION]

def sample_seed(life, case, operator_index, roster):
    index=[c['id'] for c in original_cases(roster)].index(case['id'])
    return 212000+(life*12+index)*3+operator_index
