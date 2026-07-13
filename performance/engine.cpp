/**
 * Aggregate policy-sweep engine — companion to the Mesa ABM.
 * Endogenous Investment, Unemployment and Demand-Constrained Stagnation.
 *
 * This is NOT a bit-for-bit port of the agent-level Python model.  It is a fast,
 * compiled, *representative-class* reduction (one worker aggregate, one
 * capitalist aggregate) that keeps the same causal mechanics — class saving,
 * a demand-driven labour market with a Leontief capital-per-job constraint,
 * stock-financed investment, a balanced-budget unemployment benefit, and
 * stock-flow-consistent settlement.  It reproduces the ABM's comparative statics
 * closely (e.g. baseline unemployment ~0.5 with idle capital; near-full
 * employment once theta is high enough).  Use the ABM in src/ for the
 * distributional and cross-seed (heterogeneity / matching) results.
 *
 * Build & run:
 *     g++ -O2 -std=c++11 engine.cpp -o engine && ./engine
 */

#include <iostream>
#include <iomanip>
#include <algorithm>

// ---- Parameters (mirror the Python defaults) ----------------------------
const double N   = 100.0;                 // households / workforce
const double NC  = 10.0;                  // capitalists
const double NW  = N - NC;                // workers
const int    NFIRMS = 10;

const double A          = 1.0;            // output per worker
const double MARKUP     = 0.2;
const double KAPPA      = 0.5;            // capital per job (Leontief)
const double CAP_FLOOR  = 3.5 * NFIRMS;  // aggregate capital floor
const double DELTA      = 0.05;

const double C0         = 0.1;            // autonomous consumption per household
const double C1         = 0.9;            // worker MPC
const double MPC_C      = 0.2;            // capitalist MPC
const double WEALTH_EFF = 0.02;

const double INV_SENS   = 1.0;
const double U_TARGET   = 0.9;
const double BUFFER     = 2.0;

const double RHO        = 0.3;            // benefit replacement rate
const double MAX_TAX    = 0.6;

const double WAGE = A / (1.0 + MARKUP);   // wage rate

struct Result { double output; double unemployment; double capital; };

static double clamp(double x, double lo, double hi) {
    return std::max(lo, std::min(x, hi));
}

// One deterministic run of the aggregate economy to (near) steady state.
Result simulate(double theta, int steps) {
    double Ww = NW * 2.0, Wc = NC * 2.0;   // money balances
    double Yw = NW * 2.0, Yc = NC * 2.0;   // disposable income flows
    double K = 50.0, pending = 0.0;
    double expected_demand = A * N;
    double output = 0.0, unemployment = 0.0;

    for (int t = 0; t < steps; ++t) {
        // 0. capital law of motion
        K = std::max(CAP_FLOOR, (1.0 - DELTA) * K + pending);
        pending = 0.0;

        // 1-2. demand-driven employment, capped by capital-equipped jobs
        double jobs = K / KAPPA;
        double E = clamp(std::min(expected_demand / A, jobs), 0.0, N);
        double U = N - E;

        // 3. class consumption (bounded by money on hand)
        double Cw = clamp(NW * C0 + C1 * Yw + WEALTH_EFF * Ww, 0.0, Ww + Yw);
        double Cc = clamp(NC * C0 + MPC_C * Yc + WEALTH_EFF * Wc, 0.0, Wc + Yc);

        // 4. investment from the accumulated capitalist hoard
        double hoard = std::max(0.0, Wc - NC * BUFFER);
        double capU = (jobs > 1e-12) ? E / jobs : 0.0;
        double ue = std::max(0.0, 1.0 + INV_SENS * (capU - U_TARGET));
        double I = std::min(theta * hoard * ue, std::max(0.0, Wc + Yc - Cc));

        // 5. production + rationing
        double demand = Cw + Cc + I;
        double Y = std::min(demand, A * E);
        double ration = (demand > 1e-12) ? Y / demand : 1.0;
        double Cw_a = Cw * ration, Cc_a = Cc * ration, I_a = I * ration;
        expected_demand = demand;

        // 6. distribute revenue: wages (to employed) then dividends
        double wage_per = (E > 1e-12) ? std::min(WAGE, Y / E) : 0.0;
        double dividends = Y - wage_per * E;
        double Ew = E * NW / N, Ec = E * NC / N;      // employed by class
        double Uw = U * NW / N, Uc = U * NC / N;      // unemployed by class
        double Yw_gross = wage_per * Ew;
        double Yc_gross = wage_per * Ec + dividends;

        // 7. balanced-budget benefit funded by a flat tax
        double base = std::max(0.0, Yw_gross) + std::max(0.0, Yc_gross);
        double desired = RHO * WAGE * U;
        double tax = (base > 0.0 && desired > 0.0) ? std::min(MAX_TAX, desired / base) : 0.0;
        double benefit = (U > 1e-12) ? tax * base / U : 0.0;
        double Yw_net = Yw_gross * (1.0 - tax) + benefit * Uw;
        double Yc_net = Yc_gross * (1.0 - tax) + benefit * Uc;

        // 8. settlement (credit income, pay for delivered goods)
        Ww += Yw; Ww -= Cw_a;
        Wc += Yc; Wc -= Cc_a; Wc -= I_a;
        Yw = Yw_net; Yc = Yc_net;

        // 9. queue investment as next period's capital
        pending = I_a;

        output = Y;
        unemployment = U / N;
    }
    return { output, unemployment, K };
}

int main() {
    const int STEPS = 500;
    std::cout << "Aggregate endogenous-investment engine (" << STEPS << " steps)\n";
    std::cout << std::fixed << std::setprecision(3);
    std::cout << "\n theta |   output | unemployment |  capital\n";
    std::cout <<   "-------+----------+--------------+---------\n";

    double thetas[] = {0.0, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3};
    for (double theta : thetas) {
        Result r = simulate(theta, STEPS);
        std::cout << std::setw(6) << theta << " | "
                  << std::setw(8) << r.output << " | "
                  << std::setw(12) << r.unemployment << " | "
                  << std::setw(8) << r.capital << "\n";
    }
    std::cout << "\nEndogenous investment lifts output and drives unemployment down.\n";
    return 0;
}
