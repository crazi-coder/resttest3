"""Basic context implementation for binding variables to values
"""
import logging
import types

logger = logging.getLogger('resttest3')

class Context:
    """ Manages binding of variables & generators, with both variable name and generator name being strings """

    # variables = {}
    def __init__(self):
        self.variables = {}  # Maps variable name to current value
        self.generators = {}  # Maps generator name to generator function
        self.mod_count = 0  # Lets us see if something has been altered, avoiding needless retemplating

    def bind_variable(self, variable_name, variable_value):
        """ Bind a named variable to a value within the context
            This allows for passing in variables in testing """
        str_name = str(variable_name)
        prev = self.variables.get(str_name)

        if prev != variable_value:
            self.variables[str(variable_name)] = variable_value
            self.mod_count = self.mod_count + 1
            logger.info('Context: altered variable named %s to value %s', str_name, variable_value)

    def bind_variables(self, variable_map):
        """bind variable for the key """
        for key, value in variable_map.items():
            self.bind_variable(key, value)

    def add_generator(self, generator_name, generator):
        """ Adds a generator to the context, this can be used to set values for a variable
            Once created, you can set values with the generator via bind_generator_next """

        if not isinstance(generator, types.GeneratorType):
            raise ValueError(
                'Cannot add generator named {0}, it is not a generator type'.format(generator_name))

        self.generators[str(generator_name)] = generator
        logging.debug('Context: Added generator named %s', generator_name)

    def bind_generator_next(self, variable_name, generator_name):
        """ Binds the next value for generator_name to variable_name and return value used """
        str_gen_name = str(generator_name)
        str_name = str(variable_name)
        val = next(self.generators[str_gen_name])

        prev = self.variables.get(str_name)
        if prev != val:
            self.variables[str_name] = val
            self.mod_count = self.mod_count + 1
            logging.debug(
                'Context: Set variable named %s to next value '
                '%s from generator named %s', variable_name, val, generator_name)
        return val

    def get_values(self):
        """Return the values can bind to a key """
        return self.variables

    def get_value(self, variable_name):
        """ Get bound variable value, or return none if not set """
        return self.variables.get(str(variable_name))

    def get_generators(self):
        """return all generators defined """
        return self.generators

    def get_generator(self, generator_name):
        """return generators for the given name"""
        return self.generators.get(str(generator_name))
