from src.locator_gen.locator_generator import LocatorGenerator

if __name__ == "__main__":
    html = '<input id="input" class="truncate" type="search" placeholder="Search Google or type a URL">'
    gen = LocatorGenerator()
    candidates = gen.generate_candidates(html)
    best = gen.pick_best(candidates)

    print("CANDIDATES:")
    for c in candidates[:10]:
        print(c)

    print("\nBEST:", best)
