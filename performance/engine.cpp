/**
 * Aggregate policy-sweep engine — companion to the Mesa ABM.
 * Endogenous Investment and Demand-Constrained Stagnation.
 *
 * This is NOT a bit-for-bit port of the agent-level Python model.  It is a fast,
 * compiled, *representative-agent* reduction that keeps the same causal
 * mechanics (class saving, stock-financed investment, capital-augmented
 * capacity, demand-constrained output and stock-flow-consistent settlement) and
 * reproduces the same qualitative comparative statics — output rising and the
 * output gap falling as the investment propensity theta increases.  Its purpose
 * is to scan the theta -> output relationship at compiled speed; use the ABM in
 * src/ for the distributional (heterogeneity / network) results.
 *
 * Build & run:
 *     g++ -O2 -std=c++11 engine.cpp -o engine && ./engine
 */

#include <iostream>
#include <iomanip>
#include <cmath>
#include <algorithm>

// ---- Parameters (mirror the Python defaults) ----------------------------
const int    N_HOUSEHOLDS = 100;
const int    N_CAPITALIST = 10;          // 10% of households own firms
const int    N_WORKER     = N_HOUSEHOLDS - N_CAPITALIST;
const double LABOUR       = 100.0;       // all households supply labour

const double MARKUP       = 0.2;         // profit share = MARKUP/(1+MARKUP)
const double ALPHA        = 0.5;         // capital-deepening exponent
const double GAMMA        = 0.5;         // capital-deepening weight
const double DELTA        = 0.05;        // depreciation
const double A_TFP        = 1.0;         // total factor productivity

const double C0           = 0.1;         // autonomous consumption per household
const double C1           = 0.9;         // worker MPC
const double MPC_C        = 0.4;         // capitalist MPC
const double WEALTH_EFF   = 0.02;        // propensity to consume out of wealth

const double INV_SENS     = 1.0;         // accelerator sensitivity
const double U_TARGET     = 0.8;         // target utilisation
const double BUFFER       = 2.0;         // precautionary buffer per capitalist

struct Result { double output; double potential; double capital; double gap; };

// One deterministic run of the aggregate economy to (near) steady state.
Result simulate(double theta, int steps) {
    double Ww = N_WORKER * 2.0;      // worker money balances
    double Wc = N_CAPITALIST * 2.0;  // capitalist money balances
    double Yw = N_WORKER * 2.0;      // worker income flow
    double Yc = N_CAPITALIST * 2.0;  // capitalist income flow
    double K  = 50.0;                // aggregate capital (10 firms x 5)
    double pending = 0.0;            // investment awaiting installation
    double util = 0.0;

    double output = 0.0, potential = 0.0;

    for (int t = 0; t < steps; ++t) {
        // 1. consumption demand (bounded by money on hand)
        double Cw = N_WORKER * C0 + C1    * Yw + WEALTH_EFF * Ww;
        double Cc = N_CAPITALIST * C0 + MPC_C * Yc + WEALTH_EFF * Wc;
        Cw = std::max(0.0, std::min(Cw, Ww + Yw));
        Cc = std::max(0.0, std::min(Cc, Wc + Yc));

        // 2. investment out of the accumulated capitalist hoard
        double hoard = std::max(0.0, Wc - N_CAPITALIST * BUFFER);
        double util_effect = std::max(0.0, 1.0 + INV_SENS * (util - U_TARGET));
        double I = theta * hoard * util_effect;
        double budget = std::max(0.0, Wc + Yc - Cc);   // affordability cap
        I = std::min(I, budget);

        // 3. demand, capacity, production, rationing
        double demand    = Cw + Cc + I;
        potential = A_TFP * LABOUR * (1.0 + GAMMA * std::pow(K / LABOUR, ALPHA));
        output    = std::min(demand, potential);
        double ration = (demand > 1e-12) ? output / demand : 1.0;
        util = (potential > 1e-12) ? output / potential : 0.0;

        double Cw_a = Cw * ration;
        double Cc_a = Cc * ration;
        double I_a  = I  * ration;

        // 4. distribute revenue (wages to all workers, dividends to capitalists)
        double wage_bill = output / (1.0 + MARKUP);
        double dividends = output - wage_bill;
        double Yw_new = wage_bill * (double)N_WORKER / N_HOUSEHOLDS;
        double Yc_new = wage_bill * (double)N_CAPITALIST / N_HOUSEHOLDS + dividends;

        // 5. settlement: credit income, pay for delivered goods (SFC)
        Ww += Yw; Ww -= Cw_a;
        Wc += Yc; Wc -= Cc_a; Wc -= I_a;
        Yw = Yw_new;
        Yc = Yc_new;

        // 6. capital: depreciate, then install last period's investment
        K = (1.0 - DELTA) * K + pending;
        pending = I_a;
    }

    double gap = (potential > 0.0) ? (potential - output) / potential : 0.0;
    return { output, potential, K, gap };
}

int main() {
    const int STEPS = 500;
    std::cout << "Aggregate endogenous-investment engine (" << STEPS << " steps)\n";
    std::cout << std::fixed << std::setprecision(3);
    std::cout << "\n theta |   output | potential |  capital |  gap\n";
    std::cout <<   "-------+----------+-----------+----------+------\n";

    double thetas[] = {0.0, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3};
    for (double theta : thetas) {
        Result r = simulate(theta, STEPS);
        std::cout << std::setw(6) << theta << " | "
                  << std::setw(8) << r.output << " | "
                  << std::setw(9) << r.potential << " | "
                  << std::setw(8) << r.capital << " | "
                  << std::setw(4) << r.gap << "\n";
    }
    std::cout << "\nEndogenous investment raises output and shrinks the gap.\n";
    return 0;
}
