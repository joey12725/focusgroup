from vibetest.blueprint_parser import BlueprintParser

def test_parser():
    parser = BlueprintParser()
    
    # Test range
    res_range = parser.parse("{{ range(10, 20) }}")
    print(f"Range (10-20): {res_range}")
    assert 10 <= int(res_range) <= 20

    # Test choice
    res_choice = parser.parse("{{ choice('A', 'B', 'C') }}")
    print(f"Choice (A,B,C): {res_choice}")
    assert res_choice in ['A', 'B', 'C']

    # Test weighted
    res_weighted = parser.parse("{{ weighted('High': 0.9, 'Low': 0.1) }}")
    print(f"Weighted (High:0.9, Low:0.1): {res_weighted}")
    assert res_weighted in ['High', 'Low']

    # Test normal
    res_normal = parser.parse("{{ normal(100, 10) }}")
    print(f"Normal (100, 10): {res_normal}")
    assert isinstance(res_normal, int)

    # Test bool
    res_bool = parser.parse("{{ bool(0.5) }}")
    print(f"Bool (0.5): {res_bool}")
    assert isinstance(res_bool, bool)

    # Test embedded
    res_embed = parser.parse("Age: {{ range(20, 30) }}, Mood: {{ choice('Happy', 'Sad') }}")
    print(f"Embedded: {res_embed}")
    assert "Age:" in res_embed and "Mood:" in res_embed

    print("All tests passed!")

if __name__ == "__main__":
    test_parser()
