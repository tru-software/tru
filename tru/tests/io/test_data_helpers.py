import pytest
import datetime

from tru.io.data_helpers import IsValidEmail, IsValidPostcode, ParsePrice, IsValidURL, IsValidMobile, CleanMobile, TimeInRange

"""
[tru] /home/projects/github/tru $ python -m pytest tru/tests/io/test_data_helpers.py 
"""

def test_ValidMobile():

	assert IsValidMobile("") is False
	assert IsValidMobile("1234") is False
	assert IsValidMobile("+48 500 100 20") is False

	assert IsValidMobile("500100200")
	assert IsValidMobile("+48500100200")
	assert IsValidMobile("+48 500100200")
	assert IsValidMobile("(+48)500100200")
	assert IsValidMobile("+48 500.100.200")
	assert IsValidMobile("+48-500-100-200")
	assert IsValidMobile("+48 500 100 200")


def test_CleanMobile():
	assert CleanMobile("+48 500 100 200") == "+48500100200"
	assert CleanMobile("(+48)500100200") == "+48500100200"
	assert CleanMobile("500-100-200") == "500100200"
	assert CleanMobile("500.100.200") == "500100200"


def test_IsValidPostcode():

	assert IsValidPostcode("34-430")
	assert IsValidPostcode("00-000")
	assert IsValidPostcode("00-00") is False
	assert IsValidPostcode("0") is False
	assert IsValidPostcode("") is False
	assert IsValidPostcode("00 000") is False
	assert IsValidPostcode("000-00") is False
	assert IsValidPostcode("00-0000") is False
	assert IsValidPostcode("bb-ccc") is False


def test_ParsePrice():

	assert ParsePrice("234,87") == 23487
	assert ParsePrice("234.87") == 23487
	assert ParsePrice("89 234.87") == 8923487
	assert ParsePrice("89234.87") == 8923487
	assert ParsePrice("89234") == 8923400
	assert ParsePrice("89234.9") == 8923490
	with pytest.raises(ValueError):
		assert ParsePrice("894.")
	with pytest.raises(ValueError):
		assert ParsePrice("894.879")
	with pytest.raises(ValueError):
		assert ParsePrice(".87") is False
	with pytest.raises(ValueError):
		assert ParsePrice("-234,87") is False
	with pytest.raises(ValueError):
		assert ParsePrice("-234,87") is False


def test_TimeInRange():

	now = datetime.datetime.fromisoformat("2012-12-12 10:10:10")
	assert TimeInRange(list(range(1000, 1100)),  now=now)
	assert TimeInRange(list(range(900, 1000)),  now=now) is False
	assert TimeInRange(list(range(1015, 1100)),  now=now) is False


def test_IsValidEmail():

	# https://fightingforalostcause.net/content/misc/2006/compare-email-regex.php
	# https://code.iamcal.com/php/rfc822/tests/

	invalid = r'''
1234567890123456789012345678901234567890123456789012345678@12345678901234567890123456789012345678901234567890123456789.12345678901234567890123456789012345678901234567890123456789.123456789012345678901234567890123456789012345678901234567890123.iana.org Valid Valid Valid
123456789012345678901234567890123456789012345678901234567890@12345678901234567890123456789012345678901234567890123456789.12345678901234567890123456789012345678901234567890123456789.12345678901234567890123456789012345678901234567890123456789.12345.iana.org Invalid Invalid Invalid
12345678901234567890123456789012345678901234567890123456789012345@iana.org Invalid Invalid Invalid
""@iana.org Invalid Invalid Invalid
x@x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456 Invalid Invalid Invalid
first.last@[.12.34.56.78] Invalid Invalid Invalid
first.last@[12.34.56.789] Invalid Invalid Invalid
first.last@[::12.34.56.78] Invalid Invalid Invalid
first.last@[IPv5:::12.34.56.78] Invalid Invalid Invalid
first.last@[IPv6:1111:2222:3333:4444:5555:12.34.56.78] Invalid Invalid Invalid
first.last@[IPv6:1111:2222:3333:4444:5555:6666:7777:12.34.56.78] Invalid Invalid Invalid
first.last@[IPv6:1111:2222:3333:4444:5555:6666:7777] Invalid Invalid Invalid
first.last@[IPv6:1111:2222:3333:4444:5555:6666:7777:8888:9999] Invalid Invalid Invalid
first.last@[IPv6:1111:2222::3333::4444:5555:6666] Invalid Invalid Invalid
first.last@[IPv6:1111:2222:3333::4444:5555:6666:7777] Valid Valid Valid
first.last@[IPv6:1111:2222:333x::4444:5555] Invalid Invalid Invalid
first.last@[IPv6:1111:2222:33333::4444:5555] Invalid Invalid Invalid
first.last@-xample.com Invalid Invalid Invalid
first.last@exampl-.com Invalid Invalid Invalid
first.last@x234567890123456789012345678901234567890123456789012345678901234.iana.org Invalid Invalid Invalid
test."test"@iana.org Valid Valid Valid
test@123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012.com Invalid Invalid Invalid
"test&#13;blah"@iana.org Invalid Invalid Invalid
"first"."last"@iana.org Valid Valid Valid
"first".middle."last"@iana.org Valid Valid Valid
first."last"@iana.org Valid Valid Valid
"first".last@iana.org Valid Valid Valid
"first.middle"."last"@iana.org Valid Valid Valid
first."mid\dle"."last"@iana.org Valid Valid Valid
"first"."middle"."last"@iana.org Valid Valid Valid
foo@[\1.2.3.4] Invalid Invalid Invalid
Test.&#13;&#10; Folding.&#13;&#10; Whitespace@iana.org Valid Valid Valid
first.last@[IPv6:1111:2222:3333:4444:5555:6666:12.34.567.89] Invalid Invalid Invalid
"test\&#13;&#10; blah"@iana.org Invalid Invalid Invalid
cal@iamcal(woo).(yay)com Valid Valid Valid
cal(woo(yay)hoopla)@iamcal.com Valid Valid Valid
first().last@iana.org Valid Valid Valid
first.(&#13;&#10; middle&#13;&#10; )last@iana.org Valid Valid Valid
first(Welcome to&#13;&#10; the ("wonderful" (!)) world&#13;&#10; of email)@iana.org Valid Valid Valid
jdoe@machine(comment).  example Valid Valid Valid
1234   @   local(blah)  .machine .example Valid Valid Valid
first(abc.def).last@iana.org Valid Valid Valid
first(a"bc.def).last@iana.org Valid Valid Valid
first.(")middle.last(")@iana.org Valid Valid Valid
first.last@x(1234567890123456789012345678901234567890123456789012345678901234567890).com Valid Valid Valid
a(a(b(c)d(e(f))g)h(i)j)@iana.org Valid Valid Valid
a(a(b(c)d(e(f))g)(h(i)j)@iana.org Invalid Invalid Invalid
aaa@[123.123.123.123] Valid Valid Valid
aaa@[123.123.123.123]a Invalid Invalid Invalid
aaa@[123.123.123.333] Invalid Invalid Invalid
a@-b.com Invalid Invalid Invalid
a@b-.com Invalid Invalid Invalid
invalid@about.museum- Invalid Invalid Invalid
 &#13;&#10; (&#13;&#10; x &#13;&#10; ) &#13;&#10; first&#13;&#10; ( &#13;&#10; x&#13;&#10; ) &#13;&#10; .&#13;&#10; ( &#13;&#10; x) &#13;&#10; last &#13;&#10; (  x &#13;&#10; ) &#13;&#10; @iana.org Valid Valid Valid
 test. &#13;&#10; &#13;&#10; obs@syntax.com Valid Valid Valid
first.last @iana.org Valid Valid Valid
first.last@[IPv6::] Invalid Invalid Invalid
first.last@[IPv6:::] Valid Valid Valid
first.last@[IPv6::::] Invalid Invalid Invalid
first.last@[IPv6::b4] Invalid Invalid Invalid
first.last@[IPv6:::b4] Valid Valid Valid
first.last@[IPv6::::b4] Invalid Invalid Invalid
first.last@[IPv6::b3:b4] Invalid Invalid Invalid
first.last@[IPv6:::b3:b4] Valid Valid Valid
first.last@[IPv6::::b3:b4] Invalid Invalid Invalid
first.last@[IPv6:a1::b4] Valid Valid Valid
first.last@[IPv6:a1:::b4] Invalid Invalid Invalid
first.last@[IPv6:a1:] Invalid Invalid Invalid
first.last@[IPv6:a1::] Valid Valid Valid
first.last@[IPv6:a1:::] Invalid Invalid Invalid
first.last@[IPv6:a1:a2:] Invalid Invalid Invalid
first.last@[IPv6:a1:a2::] Valid Valid Valid
first.last@[IPv6:a1:a2:::] Invalid Invalid Invalid
first.last@[IPv6:0123:4567:89ab:cdef::] Valid Valid Valid
first.last@[IPv6:0123:4567:89ab:CDEF::] Valid Valid Valid
first.last@[IPv6:::a3:a4:b1:ffff:11.22.33.44] Valid Valid Valid
first.last@[IPv6:::a2:a3:a4:b1:ffff:11.22.33.44] Valid Valid Valid
first.last@[IPv6:a1:a2:a3:a4::11.22.33.44] Valid Valid Valid
first.last@[IPv6:a1:a2:a3:a4:b1::11.22.33.44] Valid Valid Valid
first.last@[IPv6::11.22.33.44] Invalid Invalid Invalid
first.last@[IPv6::::11.22.33.44] Invalid Invalid Invalid
first.last@[IPv6:a1:11.22.33.44] Invalid Invalid Invalid
first.last@[IPv6:a1::11.22.33.44] Valid Valid Valid
first.last@[IPv6:a1:::11.22.33.44] Invalid Invalid Invalid
first.last@[IPv6:a1:a2::11.22.33.44] Valid Valid Valid
first.last@[IPv6:a1:a2:::11.22.33.44] Invalid Invalid Invalid
first.last@[IPv6:0123:4567:89ab:cdef::11.22.33.44] Valid Valid Valid
first.last@[IPv6:0123:4567:89ab:cdef::11.22.33.xx] Invalid Invalid Invalid
first.last@[IPv6:0123:4567:89ab:CDEFF::11.22.33.44] Invalid Invalid Invalid
first.last@[IPv6:a1::a4:b1::b4:11.22.33.44] Invalid Invalid Invalid
first.last@[IPv6:a1::11.22.33] Invalid Invalid Invalid
first.last@[IPv6:a1::11.22.33.44.55] Invalid Invalid Invalid
first.last@[IPv6:a1::b211.22.33.44] Invalid Invalid Invalid
first.last@[IPv6:a1::b2:11.22.33.44] Valid Valid Valid
first.last@[IPv6:a1::b2::11.22.33.44] Invalid Invalid Invalid
first.last@[IPv6:a1::b3:] Invalid Invalid Invalid
first.last@[IPv6::a2::b4] Invalid Invalid Invalid
first.last@[IPv6:a1:a2:a3:a4:b1:b2:b3:] Invalid Invalid Invalid
first.last@[IPv6::a2:a3:a4:b1:b2:b3:b4] Invalid Invalid Invalid
first.last@[IPv6:a1:a2:a3:a4::b1:b2:b3:b4] Invalid Invalid Invalid
'''

	data = r'''first.last@iana.org Valid Valid Valid
1234567890123456789012345678901234567890123456789012345678901234@iana.org Valid Valid Valid
first.last@sub.do,com Invalid Invalid Invalid
"first\"last"@iana.org Valid Valid Valid
first\@last@iana.org Invalid Invalid Invalid
"first@last"@iana.org Valid Valid Valid
"first\\last"@iana.org Valid Valid Valid
x@x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x23456789.x2 Valid Valid Valid
first.last@[12.34.56.78] Valid Valid Valid
first.last@[IPv6:::12.34.56.78] Valid Valid Valid
first.last@[IPv6:1111:2222:3333::4444:12.34.56.78] Valid Valid Valid
first.last@[IPv6:1111:2222:3333:4444:5555:6666:12.34.56.78] Valid Valid Valid
first.last@[IPv6:::1111:2222:3333:4444:5555:6666] Valid Valid Valid
first.last@[IPv6:1111:2222:3333::4444:5555:6666] Valid Valid Valid
first.last@[IPv6:1111:2222:3333:4444:5555:6666::] Valid Valid Valid
first.last@[IPv6:1111:2222:3333:4444:5555:6666:7777:8888] Valid Valid Valid
first.last@x23456789012345678901234567890123456789012345678901234567890123.iana.org Valid Valid Valid
first.last@3com.com Valid Valid Valid
first.last@123.iana.org Valid Valid Valid
first.last Invalid Invalid Invalid
.first.last@iana.org Invalid Invalid Invalid
first.last.@iana.org Invalid Invalid Invalid
first..last@iana.org Invalid Invalid Invalid
"first"last"@iana.org Invalid Invalid Invalid
"first\last"@iana.org Valid Valid Valid
"""@iana.org Invalid Invalid Invalid
"\"@iana.org Invalid Invalid Invalid
first\\@last@iana.org Invalid Invalid Invalid
first.last@ Invalid Invalid Invalid
first.last@[IPv6:1111:2222:3333::4444:5555:12.34.56.78] Valid Valid Valid
first.last@example.123 Valid Valid Invalid
first.last@com Valid Valid Invalid
"Abc\@def"@iana.org Valid Valid Valid
"Fred\ Bloggs"@iana.org Valid Valid Valid
"Joe.\\Blow"@iana.org Valid Valid Valid
"Abc@def"@iana.org Valid Valid Valid
"Fred Bloggs"@iana.org Valid Valid Valid
user+mailbox@iana.org Valid Valid Valid
customer/department=shipping@iana.org Valid Valid Valid
$A12345@iana.org Valid Valid Valid
!def!xyz%abc@iana.org Valid Valid Valid
_somename@iana.org Valid Valid Valid
dclo@us.ibm.com Valid Valid Valid
abc\@def@iana.org Invalid Invalid Invalid
abc\\@iana.org Invalid Invalid Invalid
peter.piper@iana.org Valid Valid Valid
Doug\ \"Ace\"\ Lovell@iana.org Invalid Invalid Invalid
"Doug \"Ace\" L."@iana.org Valid Valid Valid
abc@def@iana.org Invalid Invalid Invalid
abc\\@def@iana.org Invalid Invalid Invalid
abc\@iana.org Invalid Invalid Invalid
@iana.org Invalid Invalid Invalid
doug@ Invalid Invalid Invalid
"qu@iana.org Invalid Invalid Invalid
ote"@iana.org Invalid Invalid Invalid
.dot@iana.org Invalid Invalid Invalid
dot.@iana.org Invalid Invalid Invalid
two..dot@iana.org Invalid Invalid Invalid
"Doug "Ace" L."@iana.org Invalid Invalid Invalid
Doug\ \"Ace\"\ L\.@iana.org Invalid Invalid Invalid
hello world@iana.org Invalid Invalid Invalid
gatsby@f.sc.ot.t.f.i.tzg.era.l.d. Invalid Invalid Invalid
test@iana.org Valid Valid Valid
TEST@iana.org Valid Valid Valid
1234567890@iana.org Valid Valid Valid
test+test@iana.org Valid Valid Valid
test-test@iana.org Valid Valid Valid
t*est@iana.org Valid Valid Valid
+1~1+@iana.org Valid Valid Valid
{_test_}@iana.org Valid Valid Valid
"[[ test ]]"@iana.org Valid Valid Valid
test.test@iana.org Valid Valid Valid
"test.test"@iana.org Valid Valid Valid
"test@test"@iana.org Valid Valid Valid
test@123.123.123.x123 Valid Valid Valid
test@123.123.123.123 Valid Valid Invalid
test@[123.123.123.123] Valid Valid Valid
test@example.iana.org Valid Valid Valid
test@example.example.iana.org Valid Valid Valid
test.iana.org Invalid Invalid Invalid
test.@iana.org Invalid Invalid Invalid
test..test@iana.org Invalid Invalid Invalid
.test@iana.org Invalid Invalid Invalid
test@test@iana.org Invalid Invalid Invalid
test@@iana.org Invalid Invalid Invalid
-- test --@iana.org Invalid Invalid Invalid
[test]@iana.org Invalid Invalid Invalid
"test\test"@iana.org Valid Valid Valid
"test"test"@iana.org Invalid Invalid Invalid
()[]\;:,><@iana.org Invalid Invalid Invalid
test@. Invalid Invalid Invalid
test@example. Invalid Invalid Invalid
test@.org Invalid Invalid Invalid
test@example Valid Valid Invalid
test@[123.123.123.123 Invalid Invalid Invalid
test@123.123.123.123] Invalid Invalid Invalid
NotAnEmail Invalid Invalid Invalid
@NotAnEmail Invalid Invalid Invalid
"test\\blah"@iana.org Valid Valid Valid
"test\blah"@iana.org Valid Valid Valid
"test\&#13;blah"@iana.org Valid Valid Valid
"test\"blah"@iana.org Valid Valid Valid
"test"blah"@iana.org Invalid Invalid Invalid
customer/department@iana.org Valid Valid Valid
_Yosemite.Sam@iana.org Valid Valid Valid
~@iana.org Valid Valid Valid
.wooly@iana.org Invalid Invalid Invalid
wo..oly@iana.org Invalid Invalid Invalid
pootietang.@iana.org Invalid Invalid Invalid
.@iana.org Invalid Invalid Invalid
"Austin@Powers"@iana.org Valid Valid Valid
Ima.Fool@iana.org Valid Valid Valid
"Ima.Fool"@iana.org Valid Valid Valid
"Ima Fool"@iana.org Valid Valid Valid
Ima Fool@iana.org Invalid Invalid Invalid
phil.h\@\@ck@haacked.com Invalid Invalid Invalid
"first\\"last"@iana.org Invalid Invalid Invalid
"first.middle.last"@iana.org Valid Valid Valid
"first..last"@iana.org Valid Valid Valid
"first\\\"last"@iana.org Valid Valid Valid
first."".last@iana.org Invalid Invalid Invalid
first\last@iana.org Invalid Invalid Invalid
Abc\@def@iana.org Invalid Invalid Invalid
Fred\ Bloggs@iana.org Invalid Invalid Invalid
Joe.\\Blow@iana.org Invalid Invalid Invalid
"test&#13;&#10; blah"@iana.org Valid Valid Valid
{^c\@**Dog^}@cartoon.com Invalid Invalid Invalid
(foo)cal(bar)@(baz)iamcal.com(quux) Valid Valid Valid
"foo"(yay)@(hoopla)[1.2.3.4]In valid Valid Valid
cal(foo\@bar)@iamcal.com Valid Valid Valid
cal(foo\)bar)@iamcal.com Valid Valid Valid
cal(foo(bar)@iamcal.com Invalid Invalid Invalid
cal(foo)bar)@iamcal.com Invalid Invalid Invalid
cal(foo\)@iamcal.com Invalid Invalid Invalid
first(12345678901234567890123456789012345678901234567890)last@(1234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890)iana.org Invalid Invalid Invalid
pete(his account)@silly.test(his host) Valid Valid Valid
c@(Chris's host.)public.example Valid Valid Valid
first(middle)last@iana.org Invalid Invalid Invalid
first(abc("def".ghi).mno)middle(abc("def".ghi).mno).last@(abc("def".ghi).mno)example(abc("def".ghi).mno).(abc("def".ghi).mno)com(abc("def".ghi).mno) Invalid Invalid Invalid
first(abc\(def)@iana.org Valid Valid Valid
name.lastname@domain.com Valid Valid Valid
.@ Invalid Invalid Invalid
a@b Valid Valid Invalid
@bar.com Invalid Invalid Invalid
@@bar.com Invalid Invalid Invalid
a@bar.com Valid Valid Valid
aaa.com Invalid Invalid Invalid
aaa@.com Invalid Invalid Invalid
aaa@.123 Invalid Invalid Invalid
a@bar.com. Invalid Invalid Invalid
a@bar Valid Valid Invalid
a-b@bar.com Valid Valid Valid
+@b.c Valid Valid Valid
+@b.com Valid Valid Valid
-@..com Invalid Invalid Invalid
-@a..com Invalid Invalid Invalid
a@b.co-foo.uk Valid Valid Valid
"hello my name is"@stutter.com Valid Valid Valid
"Test \"Fail\" Ing"@iana.org Valid Valid Valid
valid@about.museum Valid Valid Valid
shaitan@my-domain.thisisminekthx Valid Valid Valid
test@...........com Invalid Invalid Invalid
foobar@192.168.0.1 Valid Valid Invalid
"Joe\\Blow"@iana.org Valid Valid Valid
Invalid \&#10; Folding \&#10; Whitespace@iana.org Invalid Invalid Invalid
HM2Kinsists@(that comments are allowed)this.is.ok Valid Valid Valid
user%uucp!path@berkeley.edu Valid Valid Valid
"first(last)"@iana.org Valid Valid Valid
test.&#13;&#10;&#13;&#10; obs@syntax.com Invalid Invalid Invalid
"Unicode NULL \␀"@char.com Valid Invalid Invalid
"Unicode NULL ␀"@char.com Invalid Invalid Invalid
Unicode NULL \␀@char.com Invalid Invalid Invalid
cdburgess+!#$%&'*-/=?+_{}|~test@gmail.com Valid Valid Valid
first.last@[IPv6:::a2:a3:a4:b1:b2:b3:b4] Valid Valid Valid
first.last@[IPv6:a1:a2:a3:a4:b1:b2:b3::] Valid Valid Valid
test@test.com Valid Valid Valid
test@example.com&#10;In valid Valid Valid
test@xn--example.com Valid Valid Valid
test@Bücher.ch Valid Invalid Invalid'''

	for i in data.splitlines():
		email, ExpectedStrict, ModePublic, Mode = [x[::-1] for x in i[::-1].split(" ", 3)][::-1]
		assert IsValidEmail(email, check_mx=False, verify=False) is (ExpectedStrict == 'Valid')
