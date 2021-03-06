# -*- coding: utf-8 -*-
import csv
import io
import os
import sys

import datatest
from datatest._compatibility.builtins import *
from datatest._compatibility.collections import namedtuple
from . import _unittest as unittest

try:
    import pandas
except ImportError:
    pandas = None

try:
    import xlrd
except ImportError:
    xlrd = None

try:
    import dbfread
except ImportError:
    dbfread = None

from datatest._load.get_reader import (
    get_reader,
    _from_csv_iterable,
    _from_csv_path,
)


PY2 = sys.version_info[0] == 2


try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


class SampleFilesTestCase(unittest.TestCase):
    def setUp(self):
        self.original_cwd = os.path.abspath(os.getcwd())
        os.chdir(os.path.join(os.path.dirname(__file__), 'sample_files'))

    def tearDown(self):
        os.chdir(self.original_cwd)
        # It would be best to use addCleanup() but it is not
        # available in Python 2.6.


class TestFromDicts(unittest.TestCase):
    def test_dict_records_using_fieldnames(self):
        records = [
            {'col1': 1, 'col2': 'a'},
            {'col1': 2, 'col2': 'b'},
            {'col1': 3, 'col2': 'c'},
        ]
        reader = get_reader.from_dicts(records, ['col1', 'col2'])  # <- Using fieldnames!

        expected = [
            ['col1', 'col2'],
            [1, 'a'],
            [2, 'b'],
            [3, 'c'],
        ]
        self.assertEqual(list(reader), expected)

    def test_dict_records_without_fieldnames(self):
        records = [
            {'col1': 1, 'col2': 'a'},
            {'col1': 2, 'col2': 'b'},
            {'col1': 3, 'col2': 'c'},
        ]
        reader = get_reader.from_dicts(records)  # <- No fieldnames supplied.

        reader = list(reader)
        if reader[0][0] == 'col1':  # Check for key order
            expected = [            # (not guaranteed in
                ['col1', 'col2'],   # older versions of
                [1, 'a'],           # Python).
                [2, 'b'],
                [3, 'c'],
            ]
        else:
            expected = [
                ['col2', 'col1'],
                ['a', 1],
                ['b', 2],
                ['c', 3],
            ]
        self.assertEqual(reader, expected)

    def test_empty_records(self):
        records = []

        reader = get_reader.from_dicts(records, ['col1', 'col2'])
        self.assertEqual(list(records), [])

        reader = get_reader.from_dicts(records)
        self.assertEqual(list(records), [])


class TestFromNamedtuples(unittest.TestCase):
    def test_namedtuple_records(self):
        ntup = namedtuple('ntup', ['col1', 'col2'])
        records = [
            ntup(1, 'a'),
            ntup(2, 'b'),
            ntup(3, 'c'),
        ]
        reader = get_reader.from_namedtuples(records)

        expected = [
            ('col1', 'col2'),
            (1, 'a'),
            (2, 'b'),
            (3, 'c'),
        ]
        self.assertEqual(list(reader), expected)

    def test_empty_records(self):
        records = []
        reader = get_reader.from_namedtuples(records)
        self.assertEqual(list(records), [])


class TestFromCsvIterable(unittest.TestCase):
    """Test Unicode CSV support.

    Calling _from_csv_iterable() on Python 2 uses the UnicodeReader
    and UTF8Recoder classes internally for consistent behavior across
    versions.
    """
    @staticmethod
    def get_stream(string, encoding=None):
        """Accepts string and returns file-like stream object.

        In Python 2, Unicode files should be opened in binary-mode
        but in Python 3, they should be opened in text-mode. This
        function emulates the appropriate opening behavior.
        """
        fh = io.BytesIO(string)
        if PY2:
            return fh
        return io.TextIOWrapper(fh, encoding=encoding)

    def test_ascii(self):
        stream = self.get_stream((
            b'col1,col2\n'
            b'1,a\n'
            b'2,b\n'
            b'3,c\n'
        ), encoding='ascii')

        reader = _from_csv_iterable(stream, encoding='ascii')
        expected = [
            ['col1', 'col2'],
            ['1', 'a'],
            ['2', 'b'],
            ['3', 'c'],
        ]
        self.assertEqual(list(reader), expected)

    def test_iso88591(self):
        stream = self.get_stream((
            b'col1,col2\n'
            b'1,\xe6\n'  # '\xe6' -> æ (ash)
            b'2,\xf0\n'  # '\xf0' -> ð (eth)
            b'3,\xfe\n'  # '\xfe' -> þ (thorn)
        ), encoding='iso8859-1')

        reader = _from_csv_iterable(stream, encoding='iso8859-1')
        expected = [
            ['col1', 'col2'],
            ['1', chr(0xe6)],  # chr(0xe6) -> æ
            ['2', chr(0xf0)],  # chr(0xf0) -> ð
            ['3', chr(0xfe)],  # chr(0xfe) -> þ
        ]
        self.assertEqual(list(reader), expected)

    def test_utf8(self):
        stream = self.get_stream((
            b'col1,col2\n'
            b'1,\xce\xb1\n'          # '\xce\xb1'         -> α (Greek alpha)
            b'2,\xe0\xa5\x90\n'      # '\xe0\xa5\x90'     -> ॐ (Devanagari Om)
            b'3,\xf0\x9d\x94\xb8\n'  # '\xf0\x9d\x94\xb8' -> 𝔸 (mathematical double-struck A)
        ), encoding='utf-8')

        reader = _from_csv_iterable(stream, encoding='utf-8')

        try:
            double_struck_a = chr(0x1d538)  # 𝔸
        except ValueError:
            double_struck_a = chr(0xd835) + chr(0xdd38)  # 𝔸
            # Above, we use a "surrogate pair" to support older
            # "narrow" (2-byte character) builds of Python.

        expected = [
            ['col1', 'col2'],
            ['1', chr(0x003b1)],     # α
            ['2', chr(0x00950)],     # ॐ
            ['3', double_struck_a],  # 𝔸
        ]
        self.assertEqual(list(reader), expected)

    def test_fmtparams(self):
        stream = self.get_stream((
            b'|col1| |col2|\n'
            b'|1| |a|\n'
            b'|2| |b|\n'
            b'|3| |c|\n'
        ), encoding='utf-8')

        fmtparams = {'delimiter': ' ', 'quotechar': '|'}
        reader = _from_csv_iterable(stream, encoding='utf-8', **fmtparams)
        expected = [
            ['col1', 'col2'],
            ['1', 'a'],
            ['2', 'b'],
            ['3', 'c'],
        ]
        self.assertEqual(list(reader), expected)

    def test_bad_types(self):
        bytes_literal = (
            b'col1,col2\n'
            b'1,a\n'
            b'2,b\n'
            b'3,c\n'
        )
        if PY2:
            bytes_stream = io.BytesIO(bytes_literal)
            text_stream = io.TextIOWrapper(bytes_stream, encoding='ascii')
            with self.assertRaises(TypeError):
                reader = _from_csv_iterable(text_stream, 'ascii')
        else:
            bytes_stream = io.BytesIO(bytes_literal)
            with self.assertRaises((csv.Error, TypeError)):
                reader = _from_csv_iterable(bytes_stream, 'ascii')
                list(reader)  # Trigger evaluation.

    def test_empty_file(self):
        stream = self.get_stream(b'', encoding='ascii')
        reader = _from_csv_iterable(stream, encoding='ascii')
        expected = []
        self.assertEqual(list(reader), expected)


class TestFromCsvPath(SampleFilesTestCase):
    def test_utf8(self):
        reader = _from_csv_path('sample_text_utf8.csv', encoding='utf-8')
        expected = [
            ['col1', 'col2'],
            ['utf8', chr(0x003b1)],  # chr(0x003b1) -> α
        ]
        self.assertEqual(list(reader), expected)

    def test_iso88591(self):
        reader = _from_csv_path('sample_text_iso88591.csv', encoding='iso8859-1')
        expected = [
            ['col1', 'col2'],
            ['iso88591', chr(0xe6)],  # chr(0xe6) -> æ
        ]
        self.assertEqual(list(reader), expected)

    def test_wrong_encoding(self):
        with self.assertRaises(UnicodeDecodeError):
            reader = _from_csv_path('sample_text_iso88591.csv', encoding='utf-8')
            list(reader)  # Trigger evaluation.

    def test_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            reader = _from_csv_path('missing_file.csv', encoding='iso8859-1')
            list(reader)  # Trigger evaluation.


class TestFromDatatest(unittest.TestCase):
    def setUp(self):
        self.select = datatest.Select([['A', 'B'], ['x', 1], ['y', 2]])

    def test_query_multicolumn_implicit_fieldnames(self):
        query = self.select(('B', 'A'))
        reader = get_reader.from_datatest(query)  # <- No fieldnames specified.
        self.assertEqual(list(reader), [('B', 'A'), (1, 'x'), (2, 'y')])

    def test_query_multicolumn_explicit_fieldnames(self):
        query = self.select(['B', 'A'])
        reader = get_reader.from_datatest(query, fieldnames=['foo', 'bar'])
        self.assertEqual(list(reader), [['foo', 'bar'], [1, 'x'], [2, 'y']])

    def test_query_multicolumn_non_select(self):
        query = datatest.Query.from_object([['x', 1], ['y', 2]])

        reader = get_reader.from_datatest(query)  # <- No fieldnames.
        self.assertEqual(list(reader), [['x', 1], ['y', 2]])

        reader = get_reader.from_datatest(query, fieldnames=['foo', 'bar'])
        self.assertEqual(list(reader), [['foo', 'bar'], ['x', 1], ['y', 2]])

    def test_query_singlecolumn_implicit_fieldname(self):
        query = self.select('A')
        reader = get_reader.from_datatest(query)
        self.assertEqual(list(reader), [('A',), ('x',), ('y',)])

    def test_query_singlecolumn_explicit_fieldname(self):
        query = self.select('A')
        reader = get_reader.from_datatest(query, fieldnames='foo')
        self.assertEqual(list(reader), [('foo',), ('x',), ('y',)])

    def test_query_singlecolumn_non_select(self):
        query = datatest.Query.from_object(['x', 'y'])

        reader = get_reader.from_datatest(query)  # <- No fieldnames.
        self.assertEqual(list(reader), [('x',), ('y',)])

        reader = get_reader.from_datatest(query, fieldnames='foo')
        self.assertEqual(list(reader), [('foo',), ('x',), ('y',)])

    def test_query_summed_single_value(self):
        query = self.select('B').sum()
        reader = get_reader.from_datatest(query)
        self.assertEqual(list(reader), [('B',), (3,)])

    def test_query_dict_single_key_and_value(self):
        query = self.select({'A': 'B'})
        reader = get_reader.from_datatest(query)
        self.assertEqual(list(reader), [('A', 'B'), ('x', 1), ('y', 2)])

    def test_query_dict_tuplevalue(self):
        query = self.select({'A': ('A', 'B')})
        reader = get_reader.from_datatest(query)
        self.assertEqual(list(reader), [('A', 'A', 'B'), ('x', 'x', 1), ('y', 'y', 2)])

    def test_query_dict_tuplekey(self):
        query = self.select({('A', 'A'): 'B'})
        reader = get_reader.from_datatest(query)
        self.assertEqual(list(reader), [('A', 'A', 'B'), ('x', 'x', 1), ('y', 'y', 2)])

    def test_query_dict_tuplekey_tuplevalue(self):
        query = self.select({('A', 'A'): ('B', 'B')})
        reader = get_reader.from_datatest(query)
        self.assertEqual(list(reader), [('A', 'A', 'B', 'B'), ('x', 'x', 1, 1), ('y', 'y', 2, 2)])

    def test_select_object(self):
        reader = get_reader.from_datatest(self.select)  # <- No fieldnames specified.
        self.assertEqual(list(reader), [('A', 'B'), ('x', 1), ('y', 2)])

        reader = get_reader.from_datatest(self.select, fieldnames=('foo', 'bar'))
        self.assertEqual(list(reader), [('foo', 'bar'), ('x', 1), ('y', 2)])

    def test_result_list(self):
        result = datatest.Result([['x', 1], ['y', 2]], evaluation_type=list)
        reader = get_reader.from_datatest(result)  # <- No fieldnames specified.
        self.assertEqual(list(reader), [['x', 1], ['y', 2]])

        result = datatest.Result([['x', 1], ['y', 2]], evaluation_type=list)
        reader = get_reader.from_datatest(result, fieldnames=['foo', 'bar'])
        self.assertEqual(list(reader), [['foo', 'bar'], ['x', 1], ['y', 2]])

    def test_result_dict(self):
        source_dict = {'x': [1, 1], 'y': [2]}

        result = datatest.Result(source_dict, evaluation_type=dict)
        reader = get_reader.from_datatest(result)  # <- No fieldnames specified.
        reader_list = list(reader)
        self.assertEqual(reader_list.count(('x', 1)), 2)
        self.assertEqual(reader_list.count(('y', 2)), 1)

        result = datatest.Result(source_dict, evaluation_type=dict)
        reader = get_reader.from_datatest(result, fieldnames=('foo', 'bar'))
        reader_list = list(reader)
        self.assertEqual(reader_list[0], ('foo', 'bar'))
        self.assertEqual(reader_list.count(('x', 1)), 2)
        self.assertEqual(reader_list.count(('y', 2)), 1)


@unittest.skipIf(not pandas, 'pandas not found')
class TestFromPandas(unittest.TestCase):
    def setUp(self):
        self.df = pandas.DataFrame({
            'col1': (1, 2, 3),
            'col2': ('a', 'b', 'c'),
        })

    def test_automatic_indexing(self):
        reader = get_reader.from_pandas(self.df)  # <- Includes index by default.
        expected = [
            [None, 'col1', 'col2'],
            [0, 1, 'a'],
            [1, 2, 'b'],
            [2, 3, 'c'],
        ]
        self.assertEqual(list(reader), expected)

        reader = get_reader.from_pandas(self.df, index=False)  # <- Omits index.
        expected = [
            ['col1', 'col2'],
            [1, 'a'],
            [2, 'b'],
            [3, 'c'],
        ]
        self.assertEqual(list(reader), expected)

    def test_simple_index(self):
        self.df.index = pandas.Index(['x', 'y', 'z'], name='col0')

        reader = get_reader.from_pandas(self.df)
        expected = [
            ['col0', 'col1', 'col2'],
            ['x', 1, 'a'],
            ['y', 2, 'b'],
            ['z', 3, 'c'],
        ]
        self.assertEqual(list(reader), expected)

        reader = get_reader.from_pandas(self.df, index=False)
        expected = [
            ['col1', 'col2'],
            [1, 'a'],
            [2, 'b'],
            [3, 'c'],
        ]
        self.assertEqual(list(reader), expected)

    def test_multiindex(self):
        index_values = [('x', 'one'), ('x', 'two'), ('y', 'three')]
        index = pandas.MultiIndex.from_tuples(index_values, names=['A', 'B'])
        self.df.index = index

        reader = get_reader.from_pandas(self.df)
        expected = [
            ['A', 'B', 'col1', 'col2'],
            ['x', 'one', 1, 'a'],
            ['x', 'two', 2, 'b'],
            ['y', 'three', 3, 'c'],
        ]
        self.assertEqual(list(reader), expected)

        reader = get_reader.from_pandas(self.df, index=False)
        expected = [
            ['col1', 'col2'],
            [1, 'a'],
            [2, 'b'],
            [3, 'c'],
        ]
        self.assertEqual(list(reader), expected)


@unittest.skipIf(not xlrd, 'xlrd not found')
class TestFromExcel(SampleFilesTestCase):
    def test_default_worksheet(self):
        reader = get_reader.from_excel('sample_multiworksheet.xlsx')  # <- Defaults to 1st worksheet.

        expected = [
            ['col1', 'col2'],
            [1, 'a'],
            [2, 'b'],
            [3, 'c'],
        ]
        self.assertEqual(list(reader), expected)

    def test_specified_worksheet(self):
        reader = get_reader.from_excel('sample_multiworksheet.xlsx', 'Sheet2')  # <- Specified worksheet.

        expected = [
            ['col1', 'col2'],
            [4, 'd'],
            [5, 'e'],
            [6, 'f'],
        ]
        self.assertEqual(list(reader), expected)


@unittest.skipIf(not dbfread, 'dbfread not found')
class TestFromDbf(SampleFilesTestCase):
    def test_dbf(self):
        reader = get_reader.from_dbf('sample_dbase.dbf')
        expected = [
            ['COL1', 'COL2'],
            ['dBASE', 1],
        ]
        self.assertEqual(list(reader), expected)


class TestFunctionDispatching(SampleFilesTestCase):
    def test_dicts(self):
        records = [
            {'col1': 'first'},
            {'col1': 'second'},
        ]
        reader = get_reader(records)
        expected = [['col1'], ['first'], ['second']]
        self.assertEqual(list(reader), expected)

    def test_namedtuples(self):
        ntup = namedtuple('ntup', ['col1', 'col2'])

        records = [ntup(1, 'a'), ntup(2, 'b')]
        reader = get_reader(records)

        expected = [('col1', 'col2'), (1, 'a'), (2, 'b')]
        self.assertEqual(list(reader), expected)

    def test_csv(self):
        reader = get_reader('sample_text_utf8.csv', encoding='utf-8')
        expected = [
            ['col1', 'col2'],
            ['utf8', chr(0x003b1)],  # chr(0x003b1) -> α
        ]
        self.assertEqual(list(reader), expected)

        reader = get_reader('sample_text_iso88591.csv', encoding='iso8859-1')
        expected = [
            ['col1', 'col2'],
            ['iso88591', chr(0xe6)],  # chr(0xe6) -> æ
        ]
        self.assertEqual(list(reader), expected)

        path = 'sample_text_utf8.csv'
        encoding = 'utf-8'

        def open_file(path, encoding):  # <- Helper function.
            if PY2:
                return open(path, 'rb')
            return open(path, 'rt', encoding=encoding, newline='')

        with open_file(path, encoding) as fh:
            reader = get_reader(fh, encoding=encoding)
            expected = [
                ['col1', 'col2'],
                ['utf8', chr(0x003b1)],  # chr(0x003b1) -> α
            ]
            self.assertEqual(list(reader), expected)

    def test_datatest(self):
        select = datatest.Select([['A', 'B'], ['x', 1], ['y', 2]])

        query = select(('A', 'B'))
        reader = get_reader(query)  # <- datatest.Query
        self.assertEqual(list(reader), [('A', 'B'), ('x', 1), ('y', 2)])

        reader = get_reader(select)  # <- datatest.Select
        self.assertEqual(list(reader), [('A', 'B'), ('x', 1), ('y', 2)])

        result = select({'A': 'B'}).execute()
        reader = get_reader(query)  # <- datatest.Result
        self.assertEqual(list(reader), [('A', 'B'), ('x', 1), ('y', 2)])

    @unittest.skipIf(not xlrd, 'xlrd not found')
    def test_excel(self):
        reader = get_reader('sample_excel2007.xlsx')
        expected = [
            ['col1', 'col2'],
            ['excel2007', 1],
        ]
        self.assertEqual(list(reader), expected)

        reader = get_reader('sample_excel1997.xls')
        expected = [
            ['col1', 'col2'],
            ['excel1997', 1],
        ]
        self.assertEqual(list(reader), expected)

    @unittest.skipIf(not pandas, 'pandas not found')
    def test_pandas(self):
        df = pandas.DataFrame({
            'col1': (1, 2, 3),
            'col2': ('a', 'b', 'c'),
        })
        reader = get_reader(df, index=False)
        expected = [
            ['col1', 'col2'],
            [1, 'a'],
            [2, 'b'],
            [3, 'c'],
        ]
        self.assertEqual(list(reader), expected)

    @unittest.skipIf(not dbfread, 'dbfread not found')
    def test_dbf(self):
        reader = get_reader('sample_dbase.dbf')
        expected = [
            ['COL1', 'COL2'],
            ['dBASE', 1],
        ]
        self.assertEqual(list(reader), expected)

    def test_readerlike_wrapping(self):
        """Reader-like lists should simply be wrapped."""
        readerlike = [['col1', 'col2'], [1, 'a'], [2, 'b']]
        reader = get_reader(readerlike)
        self.assertEqual(list(reader), readerlike)

        readerlike = [('col1', 'col2'), (1, 'a'), (2, 'b')]
        reader = get_reader(readerlike)
        self.assertEqual(list(reader), readerlike)

    def test_unhandled_types(self):
        """Should raise error, not return a generator."""
        with self.assertRaises(TypeError):
            get_reader(object())

        with self.assertRaises(TypeError):
            get_reader([object(), object()])
