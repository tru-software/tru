# The MIT License (MIT)

# Copyright (c) 2014 Samuel Lucidi

# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
https://github.com/mansam/validator.py/blob/master/docs/index.rst
"""

"""
validator.py

A library for validating that dictionary
values fit inside of certain sets of parameters.

Author: Samuel Lucidi <sam@samlucidi.com>

"""

__version__ = "1.2.5"

import re
from collections import namedtuple
from collections import defaultdict
from abc import ABCMeta, abstractmethod
from .data_helpers import IsValidEmail

ValidationResult = namedtuple('ValidationResult', ['valid', 'errors'])


def _isstr(s):
	"""
	Python 2/3 compatible check to see
	if an object is a string type.

	"""

	try:
		return isinstance(s, basestring)
	except NameError:
		return isinstance(s, str)

class Validator(object):
	"""
	Abstract class that advanced
	validators can inherit from in order
	to set custom error messages and such.

	"""

	__metaclass__ = ABCMeta

	err_message = {None : "failed validation"}
	not_message = {None : "failed validation"}

	def __init__(self, msg=None, not_msg=None):
		if msg:
			self.err_message.update(msg)
		if not_msg:
			self.not_message.update(not_msg)
		super().__init__()

	
	def __call__(self, *args, **kwargs):
		raise NotImplementedError

class In(Validator):
	"""
	Use to specify that the
	value of the key being
	validated must exist
	within the collection
	passed to this validator.

	# Example:
		validations = {
			"field": [In([1, 2, 3])]
		}
		passes = {"field":1}
		fails  = {"field":4}

	"""

	def __init__(self, collection, **kwargs):
		self.collection = collection
		self.err_message = {None : "Proszę wybrać z następujących z opcji %r" % collection}
		self.not_message = {None : "Proszę wybrac opcję, niebędącą jedną z następujących %r" % collection}
		super().__init__(**kwargs)

	def __call__(self, value):
		return (value in self.collection)

class Not(Validator):
	"""
	Use to negate the requirement
	of another validator. Does not
	work with Required.

	"""

	def __init__(self, validator, **kwargs):
		self.validator = validator
		self.err_message = getattr(validator, "not_message", "failed validation")
		self.not_message = getattr(validator, "err_message", "failed validation")
		super().__init__(**kwargs)

	def __call__(self, value):
		return not self.validator(value)

class Range(Validator):
	"""
	Use to specify that the value of the
	key being validated must fall between
	the start and end values. By default
	the range is inclusive, though the
	range can be made excusive by setting
	inclusive to false.
d
	# Example:
		validations = {
			"field": [Range(0, 10)]
		}
		passes = {"field": 10}
		fails = {"field" : 11}

	"""

	def __init__(self, start, end, inclusive=True, **kwargs):
		self.start = start
		self.end = end
		self.inclusive = inclusive
		self.err_message = {None : "wartość musi zawierać sie w przedziale pomiędzy %s, a %s" % (start, end)}
		self.not_message = {None : "wartość musi być spoza przedziału pomiędzy %s, a %s" % (start, end)}
		super().__init__(**kwargs)

	def __call__(self, value):
		if self.inclusive:
			return self.start <= value <= self.end
		else:
			return self.start < value < self.end

class GreaterThan(Validator):
	"""
	Use to specify that the value of the
	key being validated must be greater
	than a given value. By default the
	bound is exclusive, though the bound
	can be made inclusive by setting
	inclusive to true.

	# Example:
		validations = {
			"field": [GreaterThan(10)]
		}
		passes = {"field": 11}
		fails = {"field" : 10}

	"""

	def __init__(self, lower_bound, inclusive=False, **kwargs):
		self.lower_bound = lower_bound
		self.inclusive = inclusive
		self.err_message = {None : "wartośc musi być większa niż %s" % lower_bound}
		self.not_message = {None : "wartośc nie może być większa niż  %s" % lower_bound}
		super().__init__(**kwargs)

	def __call__(self, value):
		if self.inclusive:
			return self.lower_bound <= value
		else:
			return self.lower_bound < value

class Equals(Validator):
	"""
	Use to specify that the
	value of the key being
	validated must be equal to
	the value that was passed
	to this validator.

	# Example:
		validations = {
			"field": [Equals(1)]
		}
		passes = {"field":1}
		fails  = {"field":4}

	"""

	def __init__(self, obj, **kwargs):
		self.obj = obj
		self.err_message = {None : "wartośc musi być równa %r" % obj}
		self.not_message = {None : "wartośc nie może być równa %r" % obj}
		super().__init__(**kwargs)

	def __call__(self, value):
		return value == self.obj

class Blank(Validator):
	"""
	Use to specify that the
	value of the key being
	validated must be equal to
	the empty string.

	This is a shortcut for saying
	Equals("").

	# Example:
		validations = {
			"field": [Blank()]
		}
		passes = {"field":""}
		fails  = {"field":"four"}

	"""

	def __init__(self, **kwargs):
		self.err_message = {None : "Pole musi być puste"}
		self.not_message = {None : "Proszę uzupełnić pole"}
		super().__init__(**kwargs)

	def __call__(self, value):
		return value == ""

class Truthy(Validator):
	"""
	Use to specify that the
	value of the key being
	validated must be truthy,
	i.e. would cause an if statement
	to evaluate to True.

	# Example:
		validations = {
			"field": [Truthy()]
		}
		passes = {"field": 1}
		fails  = {"field": 0}


	"""

	def __init__(self, **kwargs):
		self.err_message = {None : "must be True-equivalent value"}
		self.not_message = {None : "must be False-equivalent value"}
		super().__init__(**kwargs)

	def __call__(self, value):
		if value:
			return True
		else:
			return False

def Required(field, dictionary):
	"""
	When added to a list of validations
	for a dictionary key indicates that
	the key must be present. This
	should not be called, just inserted
	into the list of validations.

	# Example:
		validations = {
			"field": [Required, Equals(2)]
		}

	By default, keys are considered
	optional and their validations
	will just be ignored if the field
	is not present in the dictionary
	in question.

	"""

	return (field in dictionary)


class MissingFieldMessage():

	def __init__(self, msg):
		self.message = msg

	def __call__(self, lang):
		return self.message.get(lang)


class Email(Validator):
	"""
	Use to specify that the
	value of the key being
	validated must be email,
	
	# Example:
		validations = {
			"field": [Email()]
		}
		passes = {"field": asd@asda.com}
		fails  = {"field": asda.com}


	"""

	def __init__(self, **kwargs):
		self.err_message = {None : "Proszę podać poprawny adres e-mail"}
		self.not_message = {None : "Pole nie może być adresem e-mail"}
		super().__init__(**kwargs)

	def __call__(self, value):
		if IsValidEmail(value):
			return True
		else:
			return False

class InstanceOf(Validator):
	"""
	Use to specify that the
	value of the key being
	validated must be an instance
	of the passed in base class
	or its subclasses.

	# Example:
		validations = {
			"field": [InstanceOf(basestring)]
		}
		passes = {"field": ""} # is a <'str'>, subclass of basestring
		fails  = {"field": str} # is a <'type'>

	"""

	def __init__(self, base_class, **kwargs):
		self.base_class = base_class
		self.err_message = {None : "must be an instance of %s or its subclasses" % base_class.__name__}
		self.not_message = {None : "must not be an instance of %s or its subclasses" % base_class.__name__}
		super().__init__(**kwargs)

	def __call__(self, value):
		return isinstance(value, self.base_class)

class SubclassOf(Validator):
	"""
	Use to specify that the
	value of the key being
	validated must be a subclass
	of the passed in base class.

	# Example:
		validations = {
			"field": [SubclassOf(basestring)]
		}
		passes = {"field": str} # is a subclass of basestring
		fails  = {"field": int}

	"""

	def __init__(self, base_class, **kwargs):
		self.base_class = base_class
		self.err_message = {None : "must be a subclass of %s" % base_class.__name__}
		self.not_message = {None : "must not be a subclass of %s" % base_class.__name__}
		super().__init__(**kwargs)

	def __call__(self, class_):
		return issubclass(class_, self.base_class)

class Pattern(Validator):
	"""
	Use to specify that the
	value of the key being
	validated must match the
	pattern provided to the
	validator.

	# Example:
		validations = {
			"field": [Pattern('\d\d\%')]
		}
		passes = {"field": "30%"}
		fails  = {"field": "30"}

	"""

	def __init__(self, pattern, **kwargs):
		self.pattern = pattern
		self.err_message = {None : "must match regex pattern %s" % pattern}
		self.not_message = {None : "must not match regex pattern %s" % pattern}
		self.compiled = re.compile(pattern)
		super().__init__(**kwargs)

	def __call__(self, value):
		return self.compiled.match(value)

class Then(Validator):
	"""
	Special validator for use as
	part of the If rule.
	If the conditional part of the validation
	passes, then this is used to apply another
	set of dependent rules.

	# Example:
		validations = {
			"foo": [If(Equals(1), Then({"bar": [Equals(2)]}))]
		}
		passes = {"foo": 1, "bar": 2}
		also_passes = {"foo": 2, "bar": 3}
		fails = {"foo": 1, "bar": 3}
	"""

	def __init__(self, validation, **kwargs):
		self.validation = validation
		super().__init__(**kwargs)

	def __call__(self, dictionary):
		return validate(self.validation, dictionary)

class If(Validator):
	"""
	Special conditional validator.
	If the validator passed as the first
	parameter to this function passes,
	then a second set of rules will be
	applied to the dictionary.

	# Example:
		validations = {
			"foo": [If(Equals(1), Then({"bar": [Equals(2)]}))]
		}
		passes = {"foo": 1, "bar": 2}
		also_passes = {"foo": 2, "bar": 3}
		fails = {"foo": 1, "bar": 3}
	"""

	def __init__(self, validator, then_clause, **kwargs):
		self.validator = validator
		self.then_clause = then_clause
		super().__init__(**kwargs)

	def __call__(self, value, dictionary):
		conditional = False
		dependent = None
		if self.validator(value):
			conditional = True
			dependent = self.then_clause(dictionary)
		return conditional, dependent

class Length(Validator):
	"""
	Use to specify that the
	value of the key being
	validated must have at least
	`minimum` elements and optionally
	at most `maximum` elements.

	At least one of the parameters
	to this validator must be non-zero,
	and neither may be negative.

	# Example:
		validations = {
			"field": [Length(0, maximum=5)]
		}
		passes = {"field": "hello"}
		fails  = {"field": "hello world"}

	"""

	err_messages = {
		"maximum": "must be at most {0} elements in length",
		"minimum": "must be at least {0} elements in length",
		"range": "must{0}be between {1} and {2} elements in length"
	}

	def __init__(self, minimum, maximum=0, **kwargs):
		if not minimum and not maximum:
			raise ValueError("Length must have a non-zero minimum or maximum parameter.")
		if minimum < 0 or maximum < 0:
			raise ValueError("Length cannot have negative parameters.")

		self.minimum = minimum
		self.maximum = maximum
		if minimum and maximum:
			self.err_message = {None : self.err_messages["range"].format(' ', minimum, maximum)}
			self.not_message = {None : self.err_messages["range"].format(' not ', minimum, maximum)}
		elif minimum:
			self.err_message = {None : self.err_messages["minimum"].format(minimum)}
			self.not_message = {None : self.err_messages["maximum"].format(minimum - 1)}
		elif maximum:
			self.err_message = {None : self.err_messages["maximum"].format(maximum)}
			self.not_message = {None : self.err_messages["minimum"].format(maximum + 1)}
		super().__init__(**kwargs)

	def __call__(self, value):
		if self.maximum:
			return self.minimum <= len(value) <= self.maximum
		else:
			return self.minimum <= len(value)

class Contains(Validator):
	"""
	Use to ensure that the value of the key
	being validated contains the value passed
	into the Contains validator. Works with
	any type that supports the 'in' syntax.

	# Example:
		validations = {
			"field": [Contains(3)]
		}
		passes = {"field": [1, 2, 3]}
		fails  = {"field": [4, 5, 6]}

	"""

	def __init__(self, contained, **kwargs):
		self.contained = contained
		self.err_message = {None : "must contain {0}".format(contained)}
		self.not_message = {None : "must not contain {0}".format(contained)}
		super().__init__(**kwargs)

	def __call__(self, container):
		return self.contained in container

class Each(Validator):
	"""
	Use to ensure that

	If Each is passed a list of validators, it
	just applies each of them to each element in
	the list.

	If it's instead passed a *dictionary*, it treats
	it as a validation to be applied to each element in
	the dictionary.

	"""

	def __init__(self, validations, **kwargs):
		assert isinstance(validations, (list, tuple, set, dict))
		self.validations = validations
		super().__init__(**kwargs)

	def __call__(self, container):
		assert isinstance(container, (list, tuple, set))

		# handle the "apply simple validation to each in list"
		# use case
		if isinstance(self.validations, (list, tuple, set)):
			errors = []
			for item in container:
				for v in self.validations:
					valid = v(item)
					if not valid:
						errors.append("all values " + v.err_message)

		# handle the somewhat messier list of dicts case
		if isinstance(self.validations, dict):
			errors = defaultdict(list)
			for index, item in enumerate(container):
				valid, err = validate(self.validations, item)
				if not valid:
					errors[index] = err
			errors = dict(errors)

		return (len(errors) == 0, errors)


def validate(validation, dictionary, lang=None):
	"""
	Validate that a dictionary passes a set of
	key-based validators. If all of the keys
	in the dictionary are within the parameters
	specified by the validation mapping, then
	the validation passes.

	:param validation: a mapping of keys to validators
	:type validation: dict

	:param dictionary: dictionary to be validated
	:type dictionary: dict

	:return: a tuple containing a bool indicating
	success or failure and a mapping of fields
	to error messages.

	"""

	errors = defaultdict(list)
	for key in validation:
		if isinstance(validation[key], (list, tuple)):
			if Required in validation[key]:
				if not Required(key, dictionary):
					messager = next((filter(lambda m: isinstance(m, MissingFieldMessage), validation[key])), None)
					errors[key] = [messager(lang) or messager(None) if messager else "must be present"]
					continue
			_validate_list_helper(validation, dictionary, key, errors, lang)
		else:
			v = validation[key]
			if v == Required:
				if not Required(key, dictionary):
					errors[key] = ["must be present"]
					pass
			else:
				_validate_and_store_errs(v, dictionary, key, errors, lang)
	if len(errors) > 0:
		# `errors` gets downgraded from defaultdict to dict
		# because it makes for prettier output
		return ValidationResult(valid=False, errors=[{'msg': msg, 'input': _input} for _input, msg in errors.items()])
	else:
		return ValidationResult(valid=True, errors=[])

def _validate_and_store_errs(validator, dictionary, key, errors, lang):

	# Validations shouldn't throw exceptions because of
	# type mismatches and the like. If the rule is 'Length(5)' and
	# the value in the field is 5, that should be a validation failure,
	# not a TypeError because you can't call len() on an int.
	# It's not ideal to have to hide exceptions like this because
	# there could be actual problems with a validator, but we're just going
	# to have to rely on tests preventing broken things.
	try:
		valid = validator(dictionary[key])
	except Exception:
		# Since we caught an exception while trying to validate,
		# treat it as a failure and return the normal error message
		# for that validator.
		valid = (False, validator.err_message.get(lang))
	if isinstance(valid, tuple):
		valid, errs = valid
		if errs and isinstance(errs, list):
			errors[key] += errs
		elif errs:
			errors[key].append(errs)
	elif not valid:
		# set a default error message for things like lambdas
		# and other callables that won't have an err_message set.
		msg = getattr(validator, "err_message", "failed validation")
		errors[key].append(msg.get(lang, msg.get(None, "failed validation")))

def _validate_list_helper(validation, dictionary, key, errors, lang):
	for v in validation[key]:
		# don't break on optional keys
		if key in dictionary:
			# Ok, need to deal with nested
			# validations.
			if isinstance(v, dict):
				_, nested_errors = validate(v, dictionary[key])
				if nested_errors:
					errors[key].append(nested_errors)
				continue
			# Done with that, on to the actual
			# validating bit.
			# Skip Required, since it was already
			# handled before this point.
			if isinstance(v, Validator):
				# special handling for the
				# If(Then()) form
				if isinstance(v, If):
					conditional, dependent = v(dictionary[key], dictionary)
					# if the If() condition passed and there were errors
					# in the second set of rules, then add them to the
					# list of errors for the key with the condtional
					# as a nested dictionary of errors.
					if conditional and dependent[1]:
						errors[key].append(dependent[1])
				# handling for normal validators
				else:
					_validate_and_store_errs(v, dictionary, key, errors, lang)
