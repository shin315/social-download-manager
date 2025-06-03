from localization import english
from localization import vietnamese
import inspect

def get_language_strings(module):
    """Get all string constants from a language module"""
    return {name: value for name, value in inspect.getmembers(module) 
            if not name.startswith('__') and isinstance(value, str)}

def compare_languages():
    """Compare the English and Vietnamese language strings"""
    english_strings = get_language_strings(english)
    vietnamese_strings = get_language_strings(vietnamese)
    
    print(f"English strings count: {len(english_strings)}")
    print(f"Vietnamese strings count: {len(vietnamese_strings)}")
    
    # Check for missing keys
    english_only = set(english_strings.keys()) - set(vietnamese_strings.keys())
    vietnamese_only = set(vietnamese_strings.keys()) - set(english_strings.keys())
    
    if english_only:
        print("\nStrings in English but missing in Vietnamese:")
        for key in sorted(english_only):
            print(f"  {key} = \"{english_strings[key]}\"")
    
    if vietnamese_only:
        print("\nStrings in Vietnamese but missing in English:")
        for key in sorted(vietnamese_only):
            print(f"  {key} = \"{vietnamese_strings[key]}\"")
    
    # Print only context menu strings
    print("\nContext Menu strings:")
    for key in sorted(set(english_strings.keys())):
        if key.startswith("CONTEXT_"):
            en_value = english_strings.get(key, "MISSING")
            vn_value = vietnamese_strings.get(key, "MISSING")
            print(f"{key}:")
            print(f"  EN: \"{en_value}\"")
            print(f"  VN: \"{vn_value}\"")
            print()

if __name__ == "__main__":
    compare_languages() 