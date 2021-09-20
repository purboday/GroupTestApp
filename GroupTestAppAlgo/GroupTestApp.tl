// topology configuration for RIAPS app P2PNetworkAnalyzer

for Averager.Averager {
create topology random_neighbor;
// with mode static
over (10.42.0.111, 10.42.0.112, 10.42.0.113, 10.42.0.114, 10.42.0.116, 10.42.0.118, 10.42.0.119, 10.42.0.120, 10.42.0.121, 10.42.0.122, 10.42.0.123);
// using (10.42.0.111, 10.42.0.118) , (10.42.0.116, 10.42.0.113) ;
of size 3;
inter-group communication on;
}