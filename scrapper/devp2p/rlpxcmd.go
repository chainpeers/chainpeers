// Copyright 2020 The go-ethereum Authors
// This file is part of go-ethereum.
//
// go-ethereum is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// go-ethereum is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with go-ethereum. If not, see <http://www.gnu.org/licenses/>.

package main

import (
	"errors"
	"fmt"
	"github.com/chainpeers/chainpeers/scrapper/devp2p/internal/ethtest"
	"github.com/ethereum/go-ethereum/p2p/discover/v4wire"
	"net"
	"time"

	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/p2p"
	"github.com/ethereum/go-ethereum/p2p/rlpx"
	"github.com/ethereum/go-ethereum/rlp"
	"github.com/urfave/cli/v2"
)

var (
	rlpxCommand = &cli.Command{
		Name:  "rlpx",
		Usage: "RLPx Commands",
		Subcommands: []*cli.Command{
			rlpxPingCommand,
			rlpxEthTestCommand,
			rlpxSnapTestCommand,
		},
	}
	rlpxPingCommand = &cli.Command{
		Name:   "ping",
		Usage:  "ping <node>",
		Action: rlpxPing,
	}
	rlpxEthTestCommand = &cli.Command{
		Name:      "eth-test",
		Usage:     "Runs tests against a node",
		ArgsUsage: "<node> <chain.rlp> <genesis.json>",
		Action:    rlpxEthTest,
		Flags: []cli.Flag{
			testPatternFlag,
			testTAPFlag,
		},
	}
	rlpxSnapTestCommand = &cli.Command{
		Name:      "snap-test",
		Usage:     "Runs tests against a node",
		ArgsUsage: "<node> <chain.rlp> <genesis.json>",
		Action:    rlpxSnapTest,
		Flags: []cli.Flag{
			testPatternFlag,
			testTAPFlag,
		},
	}
)

func rlpxPing(ctx *cli.Context) error {
	n := getNodeArg(ctx)
	fd, err := net.Dial("tcp", fmt.Sprintf("%v:%d", n.IP(), n.TCP()))
	if err != nil {
		return err
	}
	conn := rlpx.NewConn(fd, n.Pubkey())
	ourKey, _ := crypto.GenerateKey()
	_, err = conn.Handshake(ourKey)
	if err != nil {
		return err
	}
	code, data, _, err := conn.Read()
	if err != nil {
		return err
	}
	switch code {
	case 0:
		var h ethtest.Hello
		if err := rlp.DecodeBytes(data, &h); err != nil {
			return fmt.Errorf("invalid handshake: %v", err)
		}
		fmt.Printf("%+v\n", h)
	case 1:
		var msg []p2p.DiscReason
		if rlp.DecodeBytes(data, &msg); len(msg) == 0 {
			return errors.New("invalid disconnect message")
		}
		return fmt.Errorf("received disconnect message: %v", msg[0])
	default:
		return fmt.Errorf("invalid message code %d, expected handshake (code zero)", code)
	}
	// ping/pong
	localaddr := fd.LocalAddr().(*net.TCPAddr)
	remoteaddr := fd.RemoteAddr().(*net.TCPAddr)
	ping := v4wire.Ping{
		Version: 4,
		From: v4wire.Endpoint{
			IP:  localaddr.IP.To4(),
			TCP: uint16(localaddr.Port),
			UDP: 0,
		},
		To: v4wire.Endpoint{
			IP:  remoteaddr.IP.To4(),
			TCP: uint16(remoteaddr.Port),
			UDP: 0,
		},
		Expiration: uint64(time.Now().Add(20 * time.Second).Unix()),
	}
	packet, _, err := v4wire.Encode(ourKey, &ping)
	if err != nil {
		return err
	}
	_, err = conn.Write(v4wire.PingPacket, packet)
	if err != nil {
		return err
	}
	code, data, _, err = conn.Read()
	if err != nil {
		return err
	}
	switch code {
	case v4wire.PingPacket:
		p, _, hash, err := v4wire.Decode(data)
		if err != nil {
			return fmt.Errorf("invalid ping: %v", err)
		}
		fmt.Printf("%+v\n", p)
		pong := v4wire.Pong{
			To:         v4wire.NewEndpoint(fd.RemoteAddr().(*net.UDPAddr), 0),
			ReplyTok:   hash,
			Expiration: uint64(time.Now().Add(20 * time.Second).Unix()),
		}
		packet, _, err := v4wire.Encode(ourKey, &pong)
		if err != nil {
			return err
		}
		_, err = conn.Write(v4wire.PongPacket, packet)
		if err != nil {
			return err
		}
	case v4wire.PongPacket:
		var p v4wire.Pong
		if err := rlp.DecodeBytes(data, &p); err != nil {
			return fmt.Errorf("invalid pong: %v", err)
		}
		fmt.Printf("%+v\n", p)
	default:
		return fmt.Errorf("invalid message code %d, expected neighbors (code 4)", code)
	}

	// findnode
	findnode := v4wire.Findnode{
		Expiration: uint64(time.Now().Add(20 * time.Second).Unix()),
	}
	packet, _, err = v4wire.Encode(ourKey, &findnode)
	if err != nil {
		return err
	}
	_, err = conn.Write(v4wire.FindnodePacket, packet)
	if err != nil {
		return err
	}

	code, data, _, err = conn.Read()
	if err != nil {
		return err
	}
	switch code {
	case v4wire.NeighborsPacket:
		var h v4wire.Neighbors
		if err := rlp.DecodeBytes(data, &h); err != nil {
			return fmt.Errorf("invalid handshake: %v", err)
		}
		fmt.Printf("%+v\n", h)
	default:
		return fmt.Errorf("invalid message code %d, expected neighbors (code 4)", code)
	}
	return nil
}

// rlpxEthTest runs the eth protocol test suite.
func rlpxEthTest(ctx *cli.Context) error {
	if ctx.NArg() < 3 {
		exit("missing path to chain.rlp as command-line argument")
	}
	suite, err := ethtest.NewSuite(getNodeArg(ctx), ctx.Args().Get(1), ctx.Args().Get(2))
	if err != nil {
		exit(err)
	}
	return runTests(ctx, suite.EthTests())
}

// rlpxSnapTest runs the snap protocol test suite.
func rlpxSnapTest(ctx *cli.Context) error {
	if ctx.NArg() < 3 {
		exit("missing path to chain.rlp as command-line argument")
	}
	suite, err := ethtest.NewSuite(getNodeArg(ctx), ctx.Args().Get(1), ctx.Args().Get(2))
	if err != nil {
		exit(err)
	}
	return runTests(ctx, suite.SnapTests())
}
