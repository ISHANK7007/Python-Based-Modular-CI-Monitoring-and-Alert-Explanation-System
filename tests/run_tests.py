from test_pipeline_basic import run as test_basic
from test_pipeline_section_error import run as test_error
from test_pipeline_nested_group import run as test_nested

if __name__ == "__main__":
    print("Running all tests...\n")
    test_basic()
    print("\n")
    test_error()
    print("\n")
    test_nested()
