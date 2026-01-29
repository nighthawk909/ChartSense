"""
QA Test Script for TASK-004: Custom Exception Classes
Tests all acceptance criteria for api/exceptions.py
"""

import sys

def test_imports():
    """TEST 1: All exception classes can be imported"""
    print('='*70)
    print('TEST 1: Exception Class Imports')
    print('='*70)

    try:
        from exceptions import (
            # Base class
            ChartSenseError,
            # Alpha Vantage exceptions
            AlphaVantageError,
            AlphaVantageRateLimitError,
            AlphaVantageDataError,
            AlphaVantageAPIError,
            # Alpaca exceptions
            AlpacaError,
            AlpacaAuthError,
            AlpacaInsufficientFundsError,
            AlpacaOrderError,
            AlpacaOrderSizeTooSmallError,
            AlpacaMarketClosedError,
            AlpacaPositionError,
            AlpacaConnectionError,
            AlpacaRateLimitError,
            # Crypto exceptions
            CryptoServiceError,
            CryptoRateLimitError,
            CryptoOrderError,
            CryptoOrderSizeTooSmallError,
            CryptoInsufficientDataError,
            CryptoSymbolError,
            CryptoAPIError,
            # Utility functions
            parse_alpaca_error,
            parse_crypto_api_error,
        )
        print('[PASS] All exception classes imported successfully')
        return True
    except ImportError as e:
        print(f'[FAIL] Import error: {e}')
        return False


def test_hierarchy():
    """TEST 2: Exception hierarchy is correct"""
    print()
    print('='*70)
    print('TEST 2: Exception Hierarchy Verification')
    print('='*70)

    from exceptions import (
        ChartSenseError,
        AlphaVantageError, AlphaVantageRateLimitError, AlphaVantageDataError, AlphaVantageAPIError,
        AlpacaError, AlpacaAuthError, AlpacaInsufficientFundsError, AlpacaOrderError,
        AlpacaOrderSizeTooSmallError, AlpacaMarketClosedError, AlpacaPositionError,
        AlpacaConnectionError, AlpacaRateLimitError,
        CryptoServiceError, CryptoRateLimitError, CryptoOrderError, CryptoOrderSizeTooSmallError,
        CryptoInsufficientDataError, CryptoSymbolError, CryptoAPIError,
    )

    hierarchy_tests = [
        (ChartSenseError, Exception, 'ChartSenseError inherits from Exception'),
        (AlphaVantageError, ChartSenseError, 'AlphaVantageError inherits from ChartSenseError'),
        (AlphaVantageRateLimitError, AlphaVantageError, 'AlphaVantageRateLimitError inherits from AlphaVantageError'),
        (AlphaVantageDataError, AlphaVantageError, 'AlphaVantageDataError inherits from AlphaVantageError'),
        (AlphaVantageAPIError, AlphaVantageError, 'AlphaVantageAPIError inherits from AlphaVantageError'),
        (AlpacaError, ChartSenseError, 'AlpacaError inherits from ChartSenseError'),
        (AlpacaAuthError, AlpacaError, 'AlpacaAuthError inherits from AlpacaError'),
        (AlpacaInsufficientFundsError, AlpacaError, 'AlpacaInsufficientFundsError inherits from AlpacaError'),
        (AlpacaOrderError, AlpacaError, 'AlpacaOrderError inherits from AlpacaError'),
        (AlpacaOrderSizeTooSmallError, AlpacaOrderError, 'AlpacaOrderSizeTooSmallError inherits from AlpacaOrderError'),
        (AlpacaMarketClosedError, AlpacaError, 'AlpacaMarketClosedError inherits from AlpacaError'),
        (AlpacaPositionError, AlpacaError, 'AlpacaPositionError inherits from AlpacaError'),
        (AlpacaConnectionError, AlpacaError, 'AlpacaConnectionError inherits from AlpacaError'),
        (AlpacaRateLimitError, AlpacaError, 'AlpacaRateLimitError inherits from AlpacaError'),
        (CryptoServiceError, ChartSenseError, 'CryptoServiceError inherits from ChartSenseError'),
        (CryptoRateLimitError, CryptoServiceError, 'CryptoRateLimitError inherits from CryptoServiceError'),
        (CryptoOrderError, CryptoServiceError, 'CryptoOrderError inherits from CryptoServiceError'),
        (CryptoOrderSizeTooSmallError, CryptoOrderError, 'CryptoOrderSizeTooSmallError inherits from CryptoOrderError'),
        (CryptoInsufficientDataError, CryptoServiceError, 'CryptoInsufficientDataError inherits from CryptoServiceError'),
        (CryptoSymbolError, CryptoServiceError, 'CryptoSymbolError inherits from CryptoServiceError'),
        (CryptoAPIError, CryptoServiceError, 'CryptoAPIError inherits from CryptoServiceError'),
    ]

    all_passed = True
    passed = 0

    for child, parent, desc in hierarchy_tests:
        if issubclass(child, parent):
            print(f'[PASS] {desc}')
            passed += 1
        else:
            print(f'[FAIL] {desc}')
            all_passed = False

    print(f'\nHierarchy Tests: {passed}/{len(hierarchy_tests)} passed')
    return all_passed


def test_instantiation():
    """TEST 3: Exception instances can be created with expected parameters"""
    print()
    print('='*70)
    print('TEST 3: Exception Instantiation with Parameters')
    print('='*70)

    from exceptions import (
        ChartSenseError,
        AlphaVantageError, AlphaVantageRateLimitError, AlphaVantageDataError, AlphaVantageAPIError,
        AlpacaError, AlpacaAuthError, AlpacaInsufficientFundsError, AlpacaOrderError,
        AlpacaOrderSizeTooSmallError, AlpacaMarketClosedError, AlpacaPositionError,
        AlpacaConnectionError, AlpacaRateLimitError,
        CryptoServiceError, CryptoRateLimitError, CryptoOrderError, CryptoOrderSizeTooSmallError,
        CryptoInsufficientDataError, CryptoSymbolError, CryptoAPIError,
    )

    tests_passed = 0
    tests_failed = 0

    # Test ChartSenseError (base)
    try:
        e = ChartSenseError('Test message', error_code='TEST_CODE', details={'key': 'value'})
        assert e.message == 'Test message'
        assert e.error_code == 'TEST_CODE'
        assert e.details == {'key': 'value'}
        assert str(e) == '[TEST_CODE] Test message'
        print('[PASS] ChartSenseError instantiation')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] ChartSenseError instantiation: {ex}')
        tests_failed += 1

    # Test AlphaVantageRateLimitError
    try:
        e = AlphaVantageRateLimitError(retry_after=120)
        assert e.retry_after == 120
        assert e.error_code == 'ALPHA_VANTAGE_RATE_LIMIT'
        assert e.details['retry_after_seconds'] == 120
        print('[PASS] AlphaVantageRateLimitError instantiation')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] AlphaVantageRateLimitError instantiation: {ex}')
        tests_failed += 1

    # Test AlphaVantageDataError
    try:
        e = AlphaVantageDataError('No data for symbol', symbol='INVALID', response_data={'error': 'not found'})
        assert e.symbol == 'INVALID'
        assert e.response_data == {'error': 'not found'}
        assert e.error_code == 'ALPHA_VANTAGE_DATA_ERROR'
        print('[PASS] AlphaVantageDataError instantiation')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] AlphaVantageDataError instantiation: {ex}')
        tests_failed += 1

    # Test AlphaVantageAPIError
    try:
        e = AlphaVantageAPIError('Invalid API call', symbol='IBM')
        assert e.api_message == 'Invalid API call'
        assert e.error_code == 'ALPHA_VANTAGE_API_ERROR'
        print('[PASS] AlphaVantageAPIError instantiation')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] AlphaVantageAPIError instantiation: {ex}')
        tests_failed += 1

    # Test AlpacaAuthError
    try:
        e = AlpacaAuthError(permission_required='trading')
        assert e.permission_required == 'trading'
        assert e.error_code == 'API_PERMISSION_ERROR'
        print('[PASS] AlpacaAuthError instantiation')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] AlpacaAuthError instantiation: {ex}')
        tests_failed += 1

    # Test AlpacaInsufficientFundsError
    try:
        e = AlpacaInsufficientFundsError(required_amount=1000.0, available_amount=500.0, symbol='AAPL')
        assert e.required_amount == 1000.0
        assert e.available_amount == 500.0
        assert e.symbol == 'AAPL'
        assert e.error_code == 'INSUFFICIENT_FUNDS'
        assert 'need $1000.00' in e.message
        assert 'have $500.00' in e.message
        print('[PASS] AlpacaInsufficientFundsError instantiation')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] AlpacaInsufficientFundsError instantiation: {ex}')
        tests_failed += 1

    # Test AlpacaOrderError
    try:
        e = AlpacaOrderError('Order rejected', order_type='market', symbol='TSLA', side='buy', quantity=10.0, alpaca_message='rejected')
        assert e.order_type == 'market'
        assert e.symbol == 'TSLA'
        assert e.side == 'buy'
        assert e.quantity == 10.0
        assert e.alpaca_message == 'rejected'
        assert e.error_code == 'ORDER_ERROR'
        print('[PASS] AlpacaOrderError instantiation')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] AlpacaOrderError instantiation: {ex}')
        tests_failed += 1

    # Test AlpacaOrderSizeTooSmallError
    try:
        e = AlpacaOrderSizeTooSmallError(symbol='AAPL', quantity=0.001, minimum_notional=1.0, actual_notional=0.50)
        assert e.minimum_notional == 1.0
        assert e.actual_notional == 0.50
        assert e.error_code == 'ORDER_SIZE_TOO_SMALL'
        assert '$0.50' in e.message
        assert '$1.00' in e.message
        print('[PASS] AlpacaOrderSizeTooSmallError instantiation')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] AlpacaOrderSizeTooSmallError instantiation: {ex}')
        tests_failed += 1

    # Test AlpacaMarketClosedError
    try:
        e = AlpacaMarketClosedError(next_open='2026-01-28 09:30', current_time='2026-01-27 20:00')
        assert e.next_open == '2026-01-28 09:30'
        assert e.current_time == '2026-01-27 20:00'
        assert e.error_code == 'MARKET_CLOSED'
        print('[PASS] AlpacaMarketClosedError instantiation')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] AlpacaMarketClosedError instantiation: {ex}')
        tests_failed += 1

    # Test AlpacaPositionError
    try:
        e = AlpacaPositionError('Position not found', symbol='MSFT', operation='close')
        assert e.symbol == 'MSFT'
        assert e.operation == 'close'
        assert e.error_code == 'POSITION_ERROR'
        print('[PASS] AlpacaPositionError instantiation')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] AlpacaPositionError instantiation: {ex}')
        tests_failed += 1

    # Test AlpacaConnectionError
    try:
        e = AlpacaConnectionError(endpoint='/v2/orders', status_code=503)
        assert e.endpoint == '/v2/orders'
        assert e.status_code == 503
        assert e.error_code == 'ALPACA_CONNECTION_ERROR'
        print('[PASS] AlpacaConnectionError instantiation')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] AlpacaConnectionError instantiation: {ex}')
        tests_failed += 1

    # Test AlpacaRateLimitError
    try:
        e = AlpacaRateLimitError(retry_after=30)
        assert e.retry_after == 30
        assert e.error_code == 'RATE_LIMIT_EXCEEDED'
        print('[PASS] AlpacaRateLimitError instantiation')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] AlpacaRateLimitError instantiation: {ex}')
        tests_failed += 1

    # Test CryptoRateLimitError
    try:
        e = CryptoRateLimitError(retry_after=45)
        assert e.retry_after == 45
        assert e.error_code == 'CRYPTO_RATE_LIMIT'
        print('[PASS] CryptoRateLimitError instantiation')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] CryptoRateLimitError instantiation: {ex}')
        tests_failed += 1

    # Test CryptoOrderError
    try:
        e = CryptoOrderError('Order failed', symbol='BTCUSD', side='buy', quantity=0.1, error_message='rejected', status_code=400)
        assert e.symbol == 'BTCUSD'
        assert e.side == 'buy'
        assert e.quantity == 0.1
        assert e.error_message == 'rejected'
        assert e.status_code == 400
        assert e.error_code == 'CRYPTO_ORDER_ERROR'
        print('[PASS] CryptoOrderError instantiation')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] CryptoOrderError instantiation: {ex}')
        tests_failed += 1

    # Test CryptoOrderSizeTooSmallError
    try:
        e = CryptoOrderSizeTooSmallError(symbol='ETHUSD', quantity=0.0001, minimum_notional=1.0)
        assert e.minimum_notional == 1.0
        assert e.symbol == 'ETHUSD'
        assert e.error_code == 'CRYPTO_ORDER_SIZE_TOO_SMALL'
        print('[PASS] CryptoOrderSizeTooSmallError instantiation')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] CryptoOrderSizeTooSmallError instantiation: {ex}')
        tests_failed += 1

    # Test CryptoInsufficientDataError
    try:
        e = CryptoInsufficientDataError(symbol='BTCUSD', required_bars=100, available_bars=50)
        assert e.required_bars == 100
        assert e.available_bars == 50
        assert e.error_code == 'CRYPTO_INSUFFICIENT_DATA'
        assert 'need 100 bars' in e.message
        assert 'have 50' in e.message
        print('[PASS] CryptoInsufficientDataError instantiation')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] CryptoInsufficientDataError instantiation: {ex}')
        tests_failed += 1

    # Test CryptoSymbolError
    try:
        e = CryptoSymbolError('Invalid symbol format', symbol='BTC-USD', expected_format='BTC/USD or BTCUSD')
        assert e.symbol == 'BTC-USD'
        assert e.expected_format == 'BTC/USD or BTCUSD'
        assert e.error_code == 'SYMBOL_FORMAT_ERROR'
        print('[PASS] CryptoSymbolError instantiation')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] CryptoSymbolError instantiation: {ex}')
        tests_failed += 1

    # Test CryptoAPIError
    try:
        e = CryptoAPIError('API Error', status_code=500, api_message='Internal Server Error')
        assert e.status_code == 500
        assert e.api_message == 'Internal Server Error'
        assert e.error_code == 'CRYPTO_API_ERROR'
        print('[PASS] CryptoAPIError instantiation')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] CryptoAPIError instantiation: {ex}')
        tests_failed += 1

    print(f'\nInstantiation Tests: {tests_passed}/{tests_passed + tests_failed} passed')
    return tests_failed == 0


def test_to_dict():
    """TEST 4: to_dict() method works correctly"""
    print()
    print('='*70)
    print('TEST 4: to_dict() Method Verification')
    print('='*70)

    from exceptions import (
        ChartSenseError,
        AlpacaInsufficientFundsError,
        CryptoOrderError,
    )

    tests_passed = 0
    tests_failed = 0

    # Test base class to_dict
    try:
        e = ChartSenseError('Test error', error_code='TEST_001', details={'foo': 'bar'})
        d = e.to_dict()
        assert d['error'] == True
        assert d['error_code'] == 'TEST_001'
        assert d['message'] == 'Test error'
        assert d['details'] == {'foo': 'bar'}
        print('[PASS] ChartSenseError.to_dict() works correctly')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] ChartSenseError.to_dict(): {ex}')
        tests_failed += 1

    # Test AlpacaInsufficientFundsError to_dict
    try:
        e = AlpacaInsufficientFundsError(required_amount=1000, available_amount=500, symbol='AAPL')
        d = e.to_dict()
        assert d['error'] == True
        assert d['error_code'] == 'INSUFFICIENT_FUNDS'
        assert 'need $1000.00' in d['message']
        assert d['details']['required_amount'] == 1000
        assert d['details']['available_amount'] == 500
        assert d['details']['symbol'] == 'AAPL'
        print('[PASS] AlpacaInsufficientFundsError.to_dict() works correctly')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] AlpacaInsufficientFundsError.to_dict(): {ex}')
        tests_failed += 1

    # Test CryptoOrderError to_dict
    try:
        e = CryptoOrderError('Order failed', symbol='BTCUSD', side='buy', quantity=0.5, status_code=400)
        d = e.to_dict()
        assert d['error'] == True
        assert d['error_code'] == 'CRYPTO_ORDER_ERROR'
        assert d['details']['symbol'] == 'BTCUSD'
        assert d['details']['side'] == 'buy'
        assert d['details']['quantity'] == 0.5
        assert d['details']['status_code'] == 400
        print('[PASS] CryptoOrderError.to_dict() works correctly')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] CryptoOrderError.to_dict(): {ex}')
        tests_failed += 1

    print(f'\nto_dict() Tests: {tests_passed}/{tests_passed + tests_failed} passed')
    return tests_failed == 0


def test_raise_and_catch():
    """TEST 5: Exceptions can be raised and caught properly"""
    print()
    print('='*70)
    print('TEST 5: Raise and Catch Verification')
    print('='*70)

    from exceptions import (
        ChartSenseError,
        AlphaVantageError, AlphaVantageRateLimitError,
        AlpacaError, AlpacaInsufficientFundsError,
        CryptoServiceError, CryptoOrderError,
    )

    tests_passed = 0
    tests_failed = 0

    # Test catching specific exception
    try:
        try:
            raise AlphaVantageRateLimitError(retry_after=60)
        except AlphaVantageRateLimitError as e:
            assert e.retry_after == 60
        print('[PASS] Catch specific AlphaVantageRateLimitError')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] Catch specific AlphaVantageRateLimitError: {ex}')
        tests_failed += 1

    # Test catching parent class catches child
    try:
        try:
            raise AlphaVantageRateLimitError(retry_after=60)
        except AlphaVantageError as e:
            pass  # Should catch it
        print('[PASS] Parent AlphaVantageError catches child AlphaVantageRateLimitError')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] Parent catches child: {ex}')
        tests_failed += 1

    # Test catching base class catches all
    try:
        try:
            raise AlpacaInsufficientFundsError(required_amount=100, available_amount=50)
        except ChartSenseError as e:
            pass  # Should catch it
        print('[PASS] Base ChartSenseError catches AlpacaInsufficientFundsError')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] Base catches all: {ex}')
        tests_failed += 1

    # Test that unrelated exceptions don't catch each other
    try:
        caught_wrong = False
        try:
            raise CryptoOrderError('Test error')
        except AlpacaError:
            caught_wrong = True
        except CryptoServiceError:
            pass  # Correct
        assert not caught_wrong, 'AlpacaError should not catch CryptoOrderError'
        print('[PASS] AlpacaError does not catch CryptoOrderError')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] Exception isolation: {ex}')
        tests_failed += 1

    print(f'\nRaise/Catch Tests: {tests_passed}/{tests_passed + tests_failed} passed')
    return tests_failed == 0


def test_parse_functions():
    """TEST 6: parse_alpaca_error and parse_crypto_api_error functions"""
    print()
    print('='*70)
    print('TEST 6: Parse Error Functions')
    print('='*70)

    from exceptions import (
        parse_alpaca_error, parse_crypto_api_error,
        AlpacaAuthError, AlpacaInsufficientFundsError, AlpacaOrderSizeTooSmallError,
        AlpacaMarketClosedError, AlpacaRateLimitError, AlpacaPositionError, AlpacaOrderError,
        CryptoRateLimitError, CryptoOrderSizeTooSmallError, CryptoSymbolError, CryptoAPIError,
    )

    tests_passed = 0
    tests_failed = 0

    # Test parse_alpaca_error - authentication
    try:
        e = parse_alpaca_error('Unauthorized: Invalid API key')
        assert isinstance(e, AlpacaAuthError)
        print('[PASS] parse_alpaca_error: unauthorized -> AlpacaAuthError')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] parse_alpaca_error unauthorized: {ex}')
        tests_failed += 1

    # Test parse_alpaca_error - forbidden
    try:
        e = parse_alpaca_error('Forbidden: Access denied')
        assert isinstance(e, AlpacaAuthError)
        print('[PASS] parse_alpaca_error: forbidden -> AlpacaAuthError')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] parse_alpaca_error forbidden: {ex}')
        tests_failed += 1

    # Test parse_alpaca_error - insufficient funds
    try:
        e = parse_alpaca_error('Insufficient funds for order', symbol='AAPL')
        assert isinstance(e, AlpacaInsufficientFundsError)
        assert e.symbol == 'AAPL'
        print('[PASS] parse_alpaca_error: insufficient funds -> AlpacaInsufficientFundsError')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] parse_alpaca_error insufficient funds: {ex}')
        tests_failed += 1

    # Test parse_alpaca_error - buying power
    try:
        e = parse_alpaca_error('Buying power is not sufficient')
        assert isinstance(e, AlpacaInsufficientFundsError)
        print('[PASS] parse_alpaca_error: buying power -> AlpacaInsufficientFundsError')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] parse_alpaca_error buying power: {ex}')
        tests_failed += 1

    # Test parse_alpaca_error - order too small
    try:
        e = parse_alpaca_error('Order size too small', symbol='TSLA')
        assert isinstance(e, AlpacaOrderSizeTooSmallError)
        print('[PASS] parse_alpaca_error: too small -> AlpacaOrderSizeTooSmallError')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] parse_alpaca_error too small: {ex}')
        tests_failed += 1

    # Test parse_alpaca_error - minimum
    try:
        e = parse_alpaca_error('Below minimum notional value')
        assert isinstance(e, AlpacaOrderSizeTooSmallError)
        print('[PASS] parse_alpaca_error: minimum -> AlpacaOrderSizeTooSmallError')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] parse_alpaca_error minimum: {ex}')
        tests_failed += 1

    # Test parse_alpaca_error - market closed
    try:
        e = parse_alpaca_error('Market is closed for trading')
        assert isinstance(e, AlpacaMarketClosedError)
        print('[PASS] parse_alpaca_error: market closed -> AlpacaMarketClosedError')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] parse_alpaca_error market closed: {ex}')
        tests_failed += 1

    # Test parse_alpaca_error - rate limit
    try:
        e = parse_alpaca_error('Rate limit exceeded')
        assert isinstance(e, AlpacaRateLimitError)
        print('[PASS] parse_alpaca_error: rate limit -> AlpacaRateLimitError')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] parse_alpaca_error rate limit: {ex}')
        tests_failed += 1

    # Test parse_alpaca_error - too many requests
    try:
        e = parse_alpaca_error('Too many requests')
        assert isinstance(e, AlpacaRateLimitError)
        print('[PASS] parse_alpaca_error: too many requests -> AlpacaRateLimitError')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] parse_alpaca_error too many requests: {ex}')
        tests_failed += 1

    # Test parse_alpaca_error - position not exist
    try:
        e = parse_alpaca_error('Position does not exist', symbol='MSFT')
        assert isinstance(e, AlpacaPositionError)
        assert e.symbol == 'MSFT'
        print('[PASS] parse_alpaca_error: position not exist -> AlpacaPositionError')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] parse_alpaca_error position not exist: {ex}')
        tests_failed += 1

    # Test parse_alpaca_error - default fallback
    try:
        e = parse_alpaca_error('Unknown error occurred', symbol='AMD')
        assert isinstance(e, AlpacaOrderError)
        assert e.symbol == 'AMD'
        print('[PASS] parse_alpaca_error: default -> AlpacaOrderError')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] parse_alpaca_error default: {ex}')
        tests_failed += 1

    # Test parse_crypto_api_error - rate limit by status code
    try:
        e = parse_crypto_api_error(429, 'Some error')
        assert isinstance(e, CryptoRateLimitError)
        print('[PASS] parse_crypto_api_error: 429 -> CryptoRateLimitError')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] parse_crypto_api_error 429: {ex}')
        tests_failed += 1

    # Test parse_crypto_api_error - rate limit by message
    try:
        e = parse_crypto_api_error(400, 'Rate limit exceeded')
        assert isinstance(e, CryptoRateLimitError)
        print('[PASS] parse_crypto_api_error: rate limit message -> CryptoRateLimitError')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] parse_crypto_api_error rate limit message: {ex}')
        tests_failed += 1

    # Test parse_crypto_api_error - order too small
    try:
        e = parse_crypto_api_error(400, 'Order too small', symbol='BTCUSD')
        assert isinstance(e, CryptoOrderSizeTooSmallError)
        print('[PASS] parse_crypto_api_error: too small -> CryptoOrderSizeTooSmallError')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] parse_crypto_api_error too small: {ex}')
        tests_failed += 1

    # Test parse_crypto_api_error - minimum
    try:
        e = parse_crypto_api_error(400, 'Below minimum value')
        assert isinstance(e, CryptoOrderSizeTooSmallError)
        print('[PASS] parse_crypto_api_error: minimum -> CryptoOrderSizeTooSmallError')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] parse_crypto_api_error minimum: {ex}')
        tests_failed += 1

    # Test parse_crypto_api_error - invalid symbol
    try:
        e = parse_crypto_api_error(400, 'Symbol invalid or not found', symbol='INVALID')
        assert isinstance(e, CryptoSymbolError)
        assert e.symbol == 'INVALID'
        print('[PASS] parse_crypto_api_error: invalid symbol -> CryptoSymbolError')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] parse_crypto_api_error invalid symbol: {ex}')
        tests_failed += 1

    # Test parse_crypto_api_error - symbol not found
    try:
        e = parse_crypto_api_error(404, 'Symbol not found', symbol='UNKNOWN')
        assert isinstance(e, CryptoSymbolError)
        print('[PASS] parse_crypto_api_error: symbol not found -> CryptoSymbolError')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] parse_crypto_api_error symbol not found: {ex}')
        tests_failed += 1

    # Test parse_crypto_api_error - default fallback
    try:
        e = parse_crypto_api_error(500, 'Internal server error')
        assert isinstance(e, CryptoAPIError)
        assert e.status_code == 500
        print('[PASS] parse_crypto_api_error: default -> CryptoAPIError')
        tests_passed += 1
    except Exception as ex:
        print(f'[FAIL] parse_crypto_api_error default: {ex}')
        tests_failed += 1

    print(f'\nParse Function Tests: {tests_passed}/{tests_passed + tests_failed} passed')
    return tests_failed == 0


def main():
    """Run all QA tests"""
    print()
    print('#' * 70)
    print('#  TASK-004 QA TEST: Custom Exception Classes for API Services')
    print('#' * 70)

    results = []

    # Run all tests
    results.append(('Import Test', test_imports()))
    results.append(('Hierarchy Test', test_hierarchy()))
    results.append(('Instantiation Test', test_instantiation()))
    results.append(('to_dict() Test', test_to_dict()))
    results.append(('Raise/Catch Test', test_raise_and_catch()))
    results.append(('Parse Functions Test', test_parse_functions()))

    # Summary
    print()
    print('#' * 70)
    print('#  SUMMARY')
    print('#' * 70)

    all_passed = True
    for name, passed in results:
        status = 'PASSED' if passed else 'FAILED'
        print(f'  {name}: {status}')
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print('=' * 70)
        print('  QA PASSED: All acceptance criteria verified successfully')
        print('=' * 70)
        return 0
    else:
        print('=' * 70)
        print('  QA FAILED: Some tests did not pass')
        print('=' * 70)
        return 1


if __name__ == '__main__':
    sys.exit(main())
