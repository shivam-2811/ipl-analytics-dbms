CREATE TABLE matches (
    id INT PRIMARY KEY,
    season VARCHAR(20),
    city VARCHAR(100),
    date DATE,
    match_type VARCHAR(50),
    player_of_match VARCHAR(100),
    venue VARCHAR(255),
    team1 VARCHAR(100),
    team2 VARCHAR(100),
    toss_winner VARCHAR(100),
    toss_decision VARCHAR(20),
    winner VARCHAR(100),
    result VARCHAR(50),
    result_margin VARCHAR(50), 
    target_runs INT,
    target_overs FLOAT,
    super_over VARCHAR(5),
    method VARCHAR(50),
    umpire1 VARCHAR(100),
    umpire2 VARCHAR(100)
);

CREATE TABLE deliveries (
    delivery_id SERIAL PRIMARY KEY,
    match_id INT,
    inning INT,
    batting_team VARCHAR(100),
    bowling_team VARCHAR(100),
    over INT,
    ball INT,
    batter VARCHAR(100),
    bowler VARCHAR(100),
    non_striker VARCHAR(100),
    batsman_runs INT,
    extra_runs INT,
    total_runs INT,
    extras_type VARCHAR(50),
    is_wicket INT,
    player_dismissed VARCHAR(100),
    dismissal_kind VARCHAR(50),
    fielder VARCHAR(100),
    CONSTRAINT fk_match FOREIGN KEY(match_id) REFERENCES matches(id)
);

COPY matches FROM '/data/matches.csv' DELIMITER ',' CSV HEADER NULL 'NA';
COPY deliveries(match_id, inning, batting_team, bowling_team, over, ball, batter, bowler, non_striker, batsman_runs, extra_runs, total_runs, extras_type, is_wicket, player_dismissed, dismissal_kind, fielder) 
FROM '/data/deliveries.csv' DELIMITER ',' CSV HEADER NULL 'NA';

CREATE TABLE auction_data (
    player_name VARCHAR(100) PRIMARY KEY,
    price BIGINT
);

COPY auction_data(player_name, price) 
FROM '/data/auction.csv' DELIMITER ',' CSV HEADER NULL 'NA';