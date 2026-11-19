#!/usr/bin/env python3
"""2026-11-19: CPU-only exactness and speed screen for the sFNX lookup patch.

Read src/session.cpp on stdin; compile its actual two functions and compare
both against the original scalar semantics. Requires GNU C++ and AVX2.
"""

import pathlib
import re
import subprocess
import sys
import tempfile


RUNNER = r"""
static std::vector<int> original(const std::vector<int>& ctx, int lk, int d1) {
    std::vector<int> r;
    if (!lk || ctx.size() <= 3) return r;
    const size_t n=ctx.size()-3;
    for (size_t s=n; s-- > 0;) {
        if (!(ctx[s]==ctx[n] && ctx[s+1]==ctx[n+1] && ctx[s+2]==ctx[n+2])) continue;
        if (d1<0 || ctx[s+3]==d1) {
            int m=3;
            while (m<lk && (size_t)(m-3)<s && ctx[s-1-(m-3)]==ctx[n-1-(m-3)]) ++m;
            const int k=std::min(lk,std::max(LOOKUP_MIN,m));
            r.assign(ctx.begin()+s+3,ctx.begin()+std::min(ctx.size(),s+3+k));
        }
        break;
    }
    r.erase(std::find_if(r.begin(),r.end(),[](int t){return t>=Engine::IMAGE_TOK;}),r.end());
    return r;
}

int main(int argc,char** argv) {
    if (!__builtin_cpu_supports("avx2")) return 77;
    if (argc!=2) return 2;
    const bool enabled=std::atoi(argv[1])!=0;
    setenv("FNX_RM400_LOOKUP_AVX2",enabled?"1":"0",1);
    std::mt19937 rng(20261119);
    std::vector<int> edge(4109, 7);
    const std::vector<int> suffix{90,91,92};
    std::copy(suffix.begin(),suffix.end(),edge.end()-3);
    std::copy(suffix.begin(),suffix.end(),edge.begin()+3);
    std::copy(suffix.begin(),suffix.end(),edge.begin()+4090);
    edge[6]=19;
    edge[4093]=23;
    edge[4094]=Engine::IMAGE_TOK;
    if (!lookup_drafts(edge,6,19).empty() ||
        lookup_drafts(edge,6,23)!=std::vector<int>{23})
        throw std::runtime_error("latest-match or image-stop semantics changed");
    int cases=0;
    for (int len: {1,2,3,4,7,8,9,15,16,17,4098,4099,4100,16384,49152,262144})
      for (int repeat=0;repeat<120;++repeat) {
        const int vocab=(repeat%2)?8:248000;
        std::vector<int> c(len);
        for (auto& t:c) t=(int)(rng()%vocab);
        if (len>9 && repeat%3==0) {
            size_t near=rng()%(len-8);
            std::copy(c.end()-3,c.end(),c.begin()+near);
        }
        if (len>12 && repeat%5==0) {
            std::copy(c.end()-3,c.end(),c.begin()+2);
            c[5]=Engine::IMAGE_TOK;
        }
        for (int d: {-1,0,c[len/2]})
          for (int lk: {0,1,6,15}) {
            if (lookup_drafts(c,lk,d)!=original(c,lk,d))
                throw std::runtime_error("changed draft lookup");
            ++cases;
          }
      }
    std::cout<<cases<<" exact cases (AVX2="<<enabled<<")\n";
    int64_t sink=0;
    const char* labels[]={"miss","mid","near"};
    for(int len:{4096,16384,49152,262144})
      for(int kind=0;kind<3;++kind) {
        std::vector<int> c(len);
        for(auto& t:c) t=(int)(rng()%248000);
        for(int j=0;j<3;++j)c[len-3+j]=-1-j;
        if(kind) {
            int i=kind==1?len/2:len-8;
            std::copy(c.end()-3,c.end(),c.begin()+i);
        }
        const int rounds=6000;
        auto t0=std::chrono::steady_clock::now();
        for(int i=0;i<rounds;++i) {
            c[0]=i; // prevents invariant-hoisting of the call
            sink+=lookup_drafts(c,15,-1).size();
        }
        double us=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-t0).count()/rounds;
        std::cout<<len<<" "<<labels[kind]<<" "<<us<<" us\n";
      }
    std::cout<<"sink="<<sink<<"\n";
}
"""


def main():
    source = sys.stdin.read()
    constants = re.findall(r"constexpr int LOOKUP_(?:N|MIN)\s*=\s*\d+;", source)
    if len(constants) != 2:
        raise SystemExit("missing original lookup constants")
    start = source.index('__attribute__((target("avx2")))')
    end = source.index("\nFinish Session::generate", start)
    code = source[start:end]
    # Keep the guarded function and its dispatch, with the same env semantics.
    prelude = r"""
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <immintrin.h>
#include <iostream>
#include <random>
#include <stdexcept>
#include <vector>
// Pinned engine.hpp's synthetic image-token threshold.
struct Engine { static constexpr int IMAGE_TOK = 1 << 30; };
static bool env_flag(const char* key) { auto p=std::getenv(key); return p && std::atoi(p)!=0; }
"""
    with tempfile.TemporaryDirectory(prefix="sfnx-lookup-check-") as directory:
        path = pathlib.Path(directory)
        (path / "check.cpp").write_text(
            prelude + "\n".join(constants) + "\n#if defined(__x86_64__)\n" + code + RUNNER
        )
        subprocess.run(["g++", "-std=c++17", "-O3", "-o", str(path / "check"), str(path / "check.cpp")], check=True)
        for flags in ("0", "1", "1", "0"):
            subprocess.run([str(path / "check"), flags], check=True)


if __name__ == "__main__":
    main()
