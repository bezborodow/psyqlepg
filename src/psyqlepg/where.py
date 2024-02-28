from enum import Enum
from psycopg import sql


class ComparisonOperator(Enum):
    '''
    Comparison Operators

    https://www.postgresql.org/docs/current/functions-comparison.html
    '''
    LESS_THAN = 1
    GREATER_THAN = 2
    LESS_THAN_OR_EQUAL_TO = 3
    GREATER_THAN_OR_EQUAL_TO = 4
    EQUAL_TO = 5
    NOT_EQUAL_TO = 6


    def __str__(self):
        o = ('<', '>', '<=', '>=', '=', '!=')
        return o[self.value - 1]


    def __format__(self, spec):
        return self.__str__(self)


class Where:
    def __init__(self, name=None, value=None):
        self.params = []
        self.args = []
        if (name):
            self.append(name, value)


    def append(self, name,
               value=None,
               operator=ComparisonOperator.EQUAL_TO):

        if type(operator) is not ComparisonOperator:
            raise ValueError('Invalid comparison operator.')

        if isinstance(name, sql.Composable):
            self.params.append(name)
        else:
            self.params.append(sql.SQL('{} ' + str(operator) + ' %s').format(sql.Identifier(name)))
            self.args.append(value)
        return self


    def clause(self):
        if not self.params:
            return sql.SQL('true').format()

        return sql.SQL('{params}').format(
            params=sql.SQL(f' {self.op()} ').join(self.params))


    def as_string(self, context):
        return self.clause().as_string(context)


    def op(self):
        return 'and'


class WhereOr:
    def op(self):
        return 'or'
